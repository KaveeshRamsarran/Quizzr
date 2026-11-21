"""
PDF processing: text extraction, cleanup, structure analysis and chunking.

Everything here is synchronous and free of database access so it can run in a
worker thread (see app.services.jobs).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional, Tuple

import structlog

from app.models.document import DocumentStyle

logger = structlog.get_logger()

LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
    "­": "", "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": " - ", " ": " ", "•": "•",
}
BULLET_RE = re.compile(r"^\s*(?:[•●▪◦‣\-\*·o]|\d{1,2}[.)]|[a-z][.)])\s+")
TERMINAL_RE = re.compile(r"[.!?:;\"')\]]$")

TARGET_CHUNK_CHARS = 1600
MAX_CHUNK_CHARS = 2600

STOPWORDS = set(
    """
    a about above after again against all also am an and any are aren't as at be because been before being
    below between both but by can cannot could did do does doing down during each etc few for from further
    had has have having he her here hers herself him himself his how however i if in into is it its itself
    just let like made make many may me might more most much must my myself no nor not now of off on once
    one only or other our ours ourselves out over own per same she should since so some such than that the
    their theirs them themselves then there these they this those through thus to too under until up upon us
    use used uses using very via was we well were what when where whether which while who whom whose why
    will with within without would yet you your yours yourself yourselves page figure fig table chapter
    section example examples e.g i.e first second third new different important called known often usually
    include includes including several various way ways part parts number numbers type types kind kinds
    """.split()
)

# Words that are frequent in notes but never a study term on their own.
GENERIC_WORDS = set(
    """
    contain contains contained produce produces produced require requires required occur occurs release
    releases absorb absorbs reflect reflects break breaks store stores stored control controls provide
    provides make makes form forms help helps allow allows move moves take takes give gives show shows
    become becomes found find mainly small large high low main most each thin thick much more less often
    area areas level levels amount point points place time times case value side order rate role roles
    process processes result results effect effects thing things good best called known
    """.split()
)


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

def extract_pdf_pages(file_path: str) -> List[dict]:
    """Extract raw text page by page. Returns [{page_number, text, has_images}]."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on file
            raise ValueError("This PDF is password protected.") from exc

    pages: List[dict] = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - depends on file
            logger.warning("Page extraction failed", page=number, error=str(exc))
            text = ""
        try:
            has_images = bool(getattr(page, "images", None))
        except Exception:
            has_images = False
        pages.append({"page_number": number, "text": text, "has_images": has_images})
    return pages


def run_ocr_on_page(file_path: str, page_number: int) -> Tuple[str, float]:
    """OCR one page when pdf2image + pytesseract are installed; otherwise no-op."""
    try:
        from pdf2image import convert_from_path  # type: ignore[import-not-found]
        import pytesseract  # type: ignore[import-not-found]
    except ImportError:
        return "", 0.0
    try:
        images = convert_from_path(file_path, first_page=page_number, last_page=page_number, dpi=300)
        if not images:
            return "", 0.0
        data = pytesseract.image_to_data(images[0], output_type=pytesseract.Output.DICT)
        words, confidences = [], []
        for i, word in enumerate(data["text"]):
            if word.strip():
                words.append(word)
                conf = float(data["conf"][i])
                if conf > 0:
                    confidences.append(conf)
        avg = sum(confidences) / len(confidences) if confidences else 0.0
        return " ".join(words), avg / 100
    except Exception as exc:  # pragma: no cover - depends on system binaries
        logger.warning("OCR failed", page=page_number, error=str(exc))
        return "", 0.0


# --------------------------------------------------------------------------- #
# Cleanup
# --------------------------------------------------------------------------- #

def _normalize_chars(text: str) -> str:
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    return text


def _repeated_lines(pages: List[str]) -> set:
    """Lines (headers/footers) that repeat on many pages."""
    if len(pages) < 2:
        return set()
    counter: Counter = Counter()
    for text in pages:
        lines = {ln.strip() for ln in text.split("\n") if ln.strip()}
        counter.update(lines)
    # Short documents: only lines on every page. Longer ones: lines on half the pages.
    threshold = len(pages) if len(pages) < 4 else max(3, int(len(pages) * 0.5))
    return {line for line, count in counter.items() if count >= threshold and len(line) < 80}


def is_heading(line: str, next_line: Optional[str] = None) -> bool:
    line = line.strip()
    if not line or len(line) > 80 or len(line) < 3:
        return False
    if BULLET_RE.match(line) and not re.match(r"^\d+(\.\d+)*\s+[A-Z]", line):
        return False
    if TERMINAL_RE.search(line) and not line.endswith(":"):
        return False
    words = line.rstrip(":").split()
    if len(words) > 10:
        return False
    if not any(c.isalpha() for c in line):
        return False
    if re.match(r"^(\d+(\.\d+)*|[IVX]+\.|chapter|section|unit|lecture|part)\b", line, re.I):
        return True
    if line.isupper() and len(line) > 3:
        return True
    capitalized = sum(1 for w in words if w[:1].isupper())
    if capitalized / len(words) >= 0.6 and line[:1].isupper():
        return True
    if next_line is not None and line[:1].isupper() and len(words) <= 6 and len(next_line.strip()) > len(line) * 1.5:
        return True
    return False


def clean_page_text(text: str, drop: set) -> Tuple[str, List[str]]:
    """Rejoin wrapped lines into paragraphs; keep bullets and headings on their own lines."""
    text = _normalize_chars(text)
    # Re-join words hyphenated across a line break.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    raw_lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in raw_lines if ln and ln not in drop and not re.fullmatch(r"(page\s*)?\d{1,4}(\s*(/|of)\s*\d{1,4})?", ln, re.I)]

    out: List[str] = []
    headings: List[str] = []
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if is_heading(line, nxt):
            heading = line.rstrip(":").strip()
            headings.append(heading)
            out.append("")
            out.append(f"# {heading}")
            continue
        bullet = BULLET_RE.match(line)
        if bullet:
            marker = bullet.group(0).strip()
            rest = line[bullet.end():].strip()
            # Keep the number on numbered steps so ordered lists stay ordered.
            out.append("• " + (f"{marker.rstrip(')').rstrip('.')}. {rest}" if marker[:1].isdigit() else rest))
            continue
        if out and out[-1] and not out[-1].startswith("# ") and not TERMINAL_RE.search(out[-1]) and line[:1].islower():
            out[-1] = out[-1] + " " + line
        elif out and out[-1] and not out[-1].startswith("# ") and not out[-1].startswith("•") and not TERMINAL_RE.search(out[-1]):
            out[-1] = out[-1] + " " + line
        elif out and out[-1].startswith("•") and not TERMINAL_RE.search(out[-1]) and line[:1].islower():
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, headings[:8]


def clean_pages(raw_pages: List[dict]) -> List[dict]:
    drop = _repeated_lines([p.get("text", "") for p in raw_pages])
    cleaned = []
    for page in raw_pages:
        text, headings = clean_page_text(page.get("text", ""), drop)
        cleaned.append({**page, "text": text, "headings": headings})
    return cleaned


def display_text(text: str) -> str:
    """Strip internal heading markers for storage/display."""
    return re.sub(r"^# ", "", text, flags=re.M)


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #

def analyze_document_structure(pages: List[dict]) -> Tuple[DocumentStyle, dict]:
    total_pages = len(pages) or 1
    total_text = sum(len(p.get("text", "")) for p in pages)
    avg_text = total_text / total_pages
    all_headings = [h for p in pages for h in p.get("headings", [])]
    bullets = sum(p.get("text", "").count("•") for p in pages)
    joined = " ".join(all_headings).lower()

    if avg_text < 700 and bullets >= total_pages:
        style = DocumentStyle.SLIDES
    elif "lab" in joined.split() or "experiment" in joined or "procedure" in joined:
        style = DocumentStyle.LAB
    elif avg_text > 2200:
        style = DocumentStyle.TEXTBOOK
    else:
        style = DocumentStyle.NOTES

    structure: dict = {}
    current = None
    for heading in all_headings:
        if len(heading) < 50:
            current = heading
            structure.setdefault(heading, [])
        elif current:
            structure[current].append(heading)
    return style, structure


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #

def create_chunks(pages: List[dict], style: DocumentStyle) -> List[dict]:
    """Split cleaned pages into study chunks of roughly TARGET_CHUNK_CHARS.

    Chunks break at headings and paragraph boundaries and remember the page
    range and the heading they sit under.
    """
    chunks: List[dict] = []
    current: dict = {"parts": [], "start": None, "end": None, "heading": None, "parent": None}
    heading: Optional[str] = None
    parent: Optional[str] = None

    def flush():
        content = "\n\n".join(current["parts"]).strip()
        if len(content) >= 60:
            chunks.append({
                "start_page": current["start"],
                "end_page": current["end"],
                "content": content,
                "heading_context": current["heading"],
                "parent_heading": current["parent"],
            })
        current.update(parts=[], start=None, end=None, heading=heading, parent=parent)

    for page in pages:
        number = page["page_number"]
        blocks = [b.strip() for b in re.split(r"\n\s*\n", page.get("text", "")) if b.strip()]
        if style == DocumentStyle.SLIDES and current["parts"]:
            size = sum(len(p) for p in current["parts"])
            if size >= TARGET_CHUNK_CHARS * 0.5:
                flush()
        for block in blocks:
            lines = block.split("\n")
            if lines[0].startswith("# "):
                new_heading = lines[0][2:].strip()
                size = sum(len(p) for p in current["parts"])
                if size >= 150:
                    flush()
                parent = heading if heading and len(new_heading) > len(heading) else parent
                heading = new_heading
                if not current["parts"]:
                    current["heading"] = heading
                    current["parent"] = parent
                rest = "\n".join(lines[1:]).strip()
                # Keep the heading marker inside the chunk so the generator knows
                # which heading each line sits under (several slides can share a chunk).
                block = f"# {new_heading}\n{rest}" if rest else f"# {new_heading}"
            size = sum(len(p) for p in current["parts"])
            if size and size + len(block) > MAX_CHUNK_CHARS:
                flush()
            elif size >= TARGET_CHUNK_CHARS:
                flush()
            if current["start"] is None:
                current["start"] = number
                if current["heading"] is None:
                    current["heading"] = heading
                    current["parent"] = parent
            current["end"] = number
            # Very long single blocks are split on sentence boundaries.
            if len(block) > MAX_CHUNK_CHARS:
                sentences = re.split(r"(?<=[.!?])\s+", block)
                buf = ""
                for sentence in sentences:
                    if len(buf) + len(sentence) > TARGET_CHUNK_CHARS and buf:
                        current["parts"].append(buf.strip())
                        flush()
                        current["start"] = current["end"] = number
                        buf = ""
                    buf += sentence + " "
                if buf.strip():
                    current["parts"].append(buf.strip())
            else:
                current["parts"].append(block)
    flush()

    for chunk in chunks:
        chunk["key_terms"] = extract_key_terms(chunk["content"])
        chunk["content_type"] = detect_content_type(chunk["content"])
    return chunks


# --------------------------------------------------------------------------- #
# Lightweight text analytics
# --------------------------------------------------------------------------- #

WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']+[A-Za-z]|[A-Za-z]{2,}")


def content_words(text: str) -> List[str]:
    return [w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS and len(w) > 2]


def extract_key_terms(text: str, limit: int = 12) -> List[str]:
    """Frequent content words and capitalised phrases, most important first."""
    if not text:
        return []
    counts: Counter = Counter(
        w for w in content_words(text) if w not in GENERIC_WORDS and not w.endswith("'s")
    )
    phrases: Counter = Counter()
    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+(?:of\s+)?[A-Z][a-z]+){1,3})\b", text):
        phrase = match.group(1)
        if phrase.split()[0].lower() not in STOPWORDS:
            phrases[phrase] += 1
    scored = []
    for phrase, n in phrases.items():
        if n >= 2:
            scored.append((n * 2.5, phrase))
    for word, n in counts.items():
        if n >= 2 and len(word) >= 4:
            scored.append((float(n), word))
    scored.sort(key=lambda kv: (-kv[0], kv[1]))
    seen: set = set()
    terms: List[str] = []
    for _, term in scored:
        key = term.lower()
        if key in seen or any(key in t.lower().split() for t in terms if " " in t):
            continue
        seen.add(key)
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def detect_content_type(text: str) -> str:
    if not text:
        return "text"
    lower = text.lower()
    if re.search(r"\b(is defined as|refers to|is called|are called|is known as)\b", lower):
        return "definition"
    if re.search(r"[=±×÷∑∫]|\b(sin|cos|tan|log|ln)\b", lower):
        return "formula"
    if re.search(r"\b(step \d|first,|then,|finally,|procedure)\b", lower):
        return "process"
    if lower.count("•") >= 3:
        return "list"
    if re.search(r"\b(for example|e\.g\.|such as)\b", lower):
        return "example"
    return "text"
