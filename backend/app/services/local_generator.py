"""
Built-in flashcard and quiz generator.

Runs entirely on the server with no model, API key or network access. It reads
the chunked document text and builds study items that are grounded in the
source by construction: every card and question quotes the sentence it came
from.

What it recognises, strongest first:
  * definitions   "X is a ...", "X refers to ...", "... is called X", "X: ...",
                  "Xs are things that/who/which ...", split on "whereas/while"
  * laws          "The law of X states that ...", "Newton's first law states that ..."
  * measures      "X measures how ...", "X describes how ..."
  * people        "Gregor Mendel is known as ...", "James Watt improved the steam engine in 1769"
  * examples      "Rent control is an example of a price ceiling."
  * formulas      "(F = ma)", "calculated as W = mg"
  * complexity    slide bullets such as "Search: O(n)"
  * acronyms      "Adenosine Triphosphate (ATP)"
  * lists         "Types of mutation:" or "Steps for ...:" followed by bullets or numbers
  * key sentences sentences carrying the document's most specific terms, used for
                  fill-the-gap cards, true or false and fill in the blank
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from app.services.pdf_processing import STOPWORDS, content_words, display_text

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

PRONOUN_START = re.compile(
    r"^(it|this|that|these|those|they|there|he|she|we|you|i|which|what|who|such|here|its|their|our|his|her|one|each|both"
    r"|another|other|some|many|most|all|any|when|if|because|although|though|while|since|as|after|before|unless|until"
    r"|example|for|in|on|at|by|with|without|from|to|so|thus|then|also|however|therefore|but|and|or|a|an|the)\b",
    re.I,
)
CONTEXT_START = re.compile(r"^(it|this|that|these|those|they|he|she|we|you|i|such|here|there|its|their|his|her|our|both|another)\b", re.I)
TERM_BANNED_WORDS = {"is", "are", "was", "were", "be", "been", "has", "have", "had", "can", "will", "would", "should", "may", "do", "does", "did"}

NOT_A_TERM = set(
    """
    contain contains contained produce produces produced require requires required occur occurs occurred
    release releases released absorb absorbs absorbed reflect reflects reflected break breaks broken store
    stores stored control controls controlled provide provides provided make makes form forms formed help
    helps allow allows allowed move moves moved take takes taken give gives given show shows shown become
    becomes found find finds means mainly small large high low main most each thin thick many much more
    less often usually always never other another same different important general specific common simple
    related based following within between during across through together process processes result results
    effect effects area areas level levels state states amount amounts point points place places time times
    case cases value values side sides order rate rates role roles change changes changed object objects
    thing things item items group groups people person organism organisms number numbers part parts way ways
    increase increases decrease decreases rise rises fall falls lead leads leading example examples type types
    kind kinds set sets every equal equals greater smaller larger lower higher early late new old young long
    short good bad able known called used using uses certain several various whole first second third last
    next previous both either neither given making taking including become becoming having being
    brought made took gave began begun grew grown built wrote written held kept left met paid ran said sold
    sent stood thought told won came went became chose chosen drew drawn fell felt fought got kept knew led
    lost meant rose saw seen spent spoke taught understood
    """.split()
)

TECH_SUFFIXES = ("osis", "ase", "ism", "ology", "ics", "ity", "tion", "sion", "ment", "ance", "ence", "ous", "gen", "cyte", "ide", "ase")
HEAD_NOUNS = {"system", "movement", "class", "theory", "model", "process", "cycle", "curve", "function", "revolution", "reaction", "reactions", "force", "energy", "rate", "list", "tree", "table"}

PERSON_VERBS = {
    "invented": "invent", "improved": "improve", "built": "build", "patented": "patent", "discovered": "discover",
    "founded": "found", "developed": "develop", "designed": "design", "wrote": "write", "published": "publish",
    "proposed": "propose", "introduced": "introduce", "created": "create", "established": "establish",
    "formulated": "formulate", "described": "describe", "identified": "identify", "led": "lead", "signed": "sign",
}
NON_PERSON_WORDS = {
    "act", "acts", "revolution", "law", "laws", "war", "treaty", "empire", "kingdom", "republic", "union", "company",
    "university", "river", "ocean", "sea", "street", "system", "theory", "principle", "rule", "model", "movement",
    "industrial", "british", "french", "american", "european", "earth", "rocket", "factory", "combination", "si",
}

ABBREVIATIONS = ["e.g.", "i.e.", "etc.", "vs.", "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Fig.", "fig.", "No.", "approx.", "St.", "cf."]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")
ACRONYM_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]{1,6}s?\b")
ACRONYM_PATTERN = re.compile(r"\b((?:[A-Z][a-z]+[\s\-]+){1,5}[A-Z][a-z]+)\s+\(([A-Z]{2,8}s?)\)")
YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
FORMULA_RE = re.compile(r"\b([A-Za-z]{1,2}\s*=\s*[A-Za-z0-9][A-Za-z0-9 .*/^²³+\-]{0,14}[A-Za-z0-9²³])")
COMPLEXITY_RE = re.compile(r"^O\((?:1|n|log n|n log n|n\^?2|n²|2\^n|n!)\)$", re.I)
PERSON_RE = r"[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2}"

NOUN_PHRASE = r"[A-Za-z][\w\-'/()]*(?:\s+[\w\-'/()]+){0,6}?"

DEF_PATTERNS = [
    # X is defined as / known as / described as Y
    (re.compile(rf"^(?P<art>the|a|an)?\s*(?P<term>{NOUN_PHRASE})\s+(?P<verb>is|are)\s+(?:defined as|described as)\s+(?P<def>.{{12,}})$", re.I), "is"),
    # X refers to / means / denotes Y
    (re.compile(rf"^(?P<art>the|a|an)?\s*(?P<term>{NOUN_PHRASE})\s+(?P<verb>refers to|refer to|means|denotes|represents)\s+(?P<def>.{{12,}})$", re.I), "refers"),
    # X is a/an/the Y
    (re.compile(rf"^(?P<art>The|A|An)?\s*(?P<term>[A-Z][\w\-'/()]*(?:\s+[\w\-'/()]+){{0,6}}?)\s+(?P<verb>is|are|was|were)\s+(?P<def>(?:a|an|the|any|one of the|its|their)\s+.{{12,}})$"), "is"),
    # Xs are things that/who/which ...   (plural or past-tense category definitions)
    (re.compile(rf"^(?P<art>The)?\s*(?P<term>[A-Z][\w\-'/()]*(?:\s+[\w\-'/()]+){{0,5}}?)\s+(?P<verb>are|were|is|was)\s+(?P<def>(?:[a-z\-]+\s){{1,4}}(?:of\s(?:[a-z\-]+\s){{1,3}})?(?:that|who|which|whose|where|for which|in which)\s.{{8,}})$"), "is"),
]
CALLED_PATTERN = re.compile(r"^(?P<def>.{15,}?)\s+(?:is|are)\s+(?:called|known as|termed|referred to as)\s+(?:an?\s+|the\s+)?(?P<term>[\w\s\-']{2,50}?)[.]?$", re.I)
COLON_PATTERN = re.compile(r"^(?P<term>[A-Za-z][\w\s\-'/()]{1,50}?)\s*[:–]\s+(?P<def>[A-Za-z(].{6,})$")
LAW_PATTERN = re.compile(
    r"^(?P<term>(?:The\s+)?(?:[A-Z][\w']*\s+)?(?:[\w']+\s+){0,3}?(?:law|principle|theorem|rule|hypothesis|theory|effect)(?:\s+of\s+[\w\s\-]{2,40}?)?)\s+"
    r"(?P<verb>states|says|holds|predicts|proposes|shows)\s+that,?\s+(?:other things equal,\s+)?(?P<def>.{10,})$"
)
MEASURE_PATTERN = re.compile(rf"^(?P<art>The|A|An)?\s*(?P<term>[A-Z][\w\-'/()]*(?:\s+[\w\-'/()]+){{0,6}}?)\s+(?P<verb>measures|describes|determines|explains|predicts|shows)\s+(?P<def>(?:how|what|why|whether|when|where|the)\s.{{8,}})$")
KNOWN_AS_PERSON = re.compile(rf"^(?P<who>{PERSON_RE})\s+(?:is|was)\s+(?:known|remembered|regarded|often called|called)\s+as\s+(?P<what>the\s.{{6,}}?)\.?$")
EXAMPLE_PATTERN = re.compile(r"^(?P<ex>[A-Z][\w\s\-']{2,50}?)\s+(?:is|are)\s+(?:a|an|one)\s+(?:common\s+|classic\s+|good\s+|typical\s+|well-known\s+)?examples?\s+of\s+(?:an?\s+|the\s+)?(?P<of>[\w\s\-']{3,50}?)\.?$")
EVENT_ACTIVE = re.compile(
    rf"^(?:In\s+(?P<year1>\d{{4}}),\s+)?(?P<who>{PERSON_RE})\s+(?P<verb>{'|'.join(PERSON_VERBS)})\s+(?P<obj>(?:the|a|an|his|her|their)\s[^,;]+?)"
    rf"(?:\s+in\s+(?P<year2>\d{{4}}))?(?=,|\s+by\s|\s+which|\s+to\s|\.|;|$)"
)
EVENT_PASSIVE = re.compile(
    rf"^(?P<obj>The\s[\w\s\-']+?),\s+(?P<verb>{'|'.join(PERSON_VERBS)})\s+by\s+(?P<who>{PERSON_RE})(?:\s+in\s+(?P<year>\d{{4}}))?,"
)
LIST_LEAD = re.compile(
    r"^(?:the\s+)?(?:\d+\s+)?(types|kinds|forms|classes|categories|stages|phases|steps|causes|effects|features|properties|functions|examples|"
    r"advantages|disadvantages|characteristics|principles|components|parts|methods|rules|uses|symptoms|factors|benefits|levels|layers)\b",
    re.I,
)


@dataclass
class Fact:
    kind: str
    chunk_id: Optional[int]
    pages: List[int]
    topic: Optional[str]
    source: str
    term: str = ""
    definition: str = ""
    items: List[str] = field(default_factory=list)
    score: float = 0.0
    plural: bool = False
    article: str = ""
    verb: str = "is"
    answer: str = ""
    question: str = ""
    year: str = ""
    ordered: bool = False
    colon: bool = False


@dataclass
class ChunkInput:
    id: Optional[int]
    content: str
    start_page: int
    end_page: int
    heading: Optional[str] = None


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

def _protect_abbreviations(text: str) -> str:
    for abbr in ABBREVIATIONS:
        text = text.replace(abbr, abbr.replace(".", "․"))
    return text


def _restore(text: str) -> str:
    return text.replace("․", ".")


def split_sentences(text: str) -> List[str]:
    sentences: List[str] = []
    for block in re.split(r"\n+", text):
        block = block.strip()
        if not block or block.startswith("# "):
            continue
        if block.startswith("•"):
            sentences.append(_restore(block.lstrip("• ").strip()))
            continue
        for sentence in SENTENCE_SPLIT.split(_protect_abbreviations(block)):
            sentence = _restore(sentence.strip())
            if sentence:
                sentences.append(sentence)
    return sentences


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" •-*·")


def _is_good_sentence(s: str, min_words: int = 6, max_words: int = 45) -> bool:
    words = s.split()
    if not (min_words <= len(words) <= max_words):
        return False
    letters = sum(c.isalpha() for c in s)
    if letters < len(s) * 0.6:
        return False
    if "http" in s or "www." in s or "@" in s or s.endswith("?"):
        return False
    return True


def _good_term(term: str) -> bool:
    term = term.strip()
    words = term.split()
    if not (1 <= len(words) <= 6) or len(term) < 2 or len(term) > 60:
        return False
    if PRONOUN_START.match(term):
        return False
    if any(w.lower() in TERM_BANNED_WORDS for w in words):
        return False
    if words[-1].lower() in STOPWORDS:
        return False
    if len(words) == 1 and words[0].lower() in STOPWORDS:
        return False
    return any(c.isalpha() for c in term)


def _strip_article(term: str) -> str:
    return re.sub(r"^(the|a|an)\s+", "", term.strip(), flags=re.I).strip()


def _sentence_case(text: str) -> str:
    text = text.strip()
    return text[:1].upper() + text[1:] if text else text


def _lower_first(text: str) -> str:
    text = text.strip()
    if len(text) > 1 and text[1:2].isupper():  # acronym such as "DNA"
        return text
    return text[:1].lower() + text[1:] if text else text


def _end(text: str) -> str:
    text = text.strip().rstrip(",;:")
    return text if re.search(r"[.!?]$", text) else text + "."


def _trim(text: str, limit: int = 220) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "..."


def _fix_articles(text: str) -> str:
    text = re.sub(r"\b([Aa]) (?=[aeiouAEIOU](?!ni|ser|nique))", lambda m: m.group(1) + "n ", text)
    return re.sub(r"\b([Aa])n (?=[^aeiouAEIOU\W_])", lambda m: m.group(1) + " ", text)


def _article_for(word: str) -> str:
    return "an " if word[:1].lower() in "aeiou" else "a "


def _is_plural(term: str) -> bool:
    last = term.split()[-1].lower().rstrip(")")
    if "(" in term:
        last = term.split("(")[0].split()[-1].lower()
    return last.endswith("s") and not last.endswith(("ss", "us", "is", "sis", "ics"))


def _normalize_for_matching(sentence: str) -> str:
    s = re.sub(r",\s+such as [^,]+,", "", sentence)
    s = re.sub(r"^(?:Example|Note|Definition|Recall|Remember):\s+", "", s)
    return s.rstrip(".").strip()


# --------------------------------------------------------------------------- #
# Fact extraction
# --------------------------------------------------------------------------- #

class FactExtractor:
    def __init__(self, chunks: Sequence[ChunkInput]):
        self.chunks = list(chunks)
        self.all_text = "\n".join(display_text(c.content) for c in self.chunks)
        self.tf: Counter = Counter(content_words(self.all_text))
        self.doc_terms = self._document_terms()
        self.headings = [c.heading for c in self.chunks if c.heading]
        self.persons: Set[str] = set()
        self._known_terms: Set[str] = set()

    # ---- weights ------------------------------------------------------------

    def _document_terms(self) -> Dict[str, float]:
        df: Counter = Counter()
        for chunk in self.chunks:
            df.update(set(content_words(chunk.content)))
        n = max(1, len(self.chunks))
        weights: Dict[str, float] = {}
        for word, count in self.tf.items():
            if count < 2 or len(word) < 4:
                continue
            weights[word] = math.log(1 + count) * (0.6 + math.log(1 + n / df[word]))
        return weights

    def term_weight(self, term: str) -> float:
        words = content_words(term)
        if not words:
            return 0.0
        return sum(self.doc_terms.get(w, 0.0) for w in words) / len(words) + 0.3 * (len(words) - 1)

    # ---- term display -------------------------------------------------------

    def _capitalised_mid_sentence(self, word: str) -> bool:
        for m in re.finditer(rf"(?<![\w']){re.escape(word)}\b", self.all_text):
            prefix = self.all_text[max(0, m.start() - 200):m.start()]
            cut = max(prefix.rfind("\n"), *(prefix.rfind(p) for p in (". ", "! ", "? ", ": ", "; ")))
            if not prefix[cut + 1:].strip(" \u2022#"):
                continue  # first word of a sentence, line or bullet
            return True
        return False

    def display_term(self, term: str) -> str:
        """Lower-case a term capitalised only because it opened a sentence or a bullet."""
        words = term.split()
        if not words or not term[:1].isupper():
            return term
        first = words[0]
        if ACRONYM_TOKEN.fullmatch(first.rstrip("'s")) or term in self.persons:
            return term
        if any(w[:1].isupper() and not w.startswith("(") for w in words[1:]):
            return term  # a proper name such as "Industrial Revolution"
        if self._capitalised_mid_sentence(first):
            return term  # "Punnett square", "Newton's first law"
        return _lower_first(term)

    def _make_definition(self, chunk, pages, topic, source, term, definition, verb="is", article="", colon=False, base=3.0) -> Optional[Fact]:
        lead = re.match(r"^(the|a|an)\s+", term.strip(), re.I)
        if lead and not article:
            article = lead.group(1)
        term = _strip_article(term).strip(" ,")
        definition = definition.strip().rstrip(".").strip()
        if not _good_term(term) or len(definition.split()) < 3:
            return None
        if re.match(r"^(?:a|an|one)\s+(?:common\s+|classic\s+|good\s+|typical\s+)?example of\b", definition, re.I):
            return None  # handled as an example fact
        fact = Fact(
            "definition", chunk.id, pages, topic, source,
            term=term, definition=_end(_sentence_case(definition)), score=base + self.term_weight(term),
            verb=verb.lower(), colon=colon,
        )
        art = (article or "").lower()
        fact.article = f"{art} " if art in {"a", "an", "the"} else ""
        fact.plural = verb.lower() in {"are", "were"} or (verb.lower() == "refer") or (not fact.article and _is_plural(term) and verb.lower() not in {"is", "was"})
        if colon and not fact.article:
            if re.match(r"^(a|an)\s", definition, re.I) and not _is_plural(term):
                fact.article = _article_for(term)
            elif not _is_plural(term) and not term.lower().endswith(("ing", "ism", "ity", "ness", "sis")) and term[:1].islower() is False and re.match(r"^[a-z]+s\s", definition):
                fact.article = ""
        fact.term = self.display_term(term)
        if colon and not fact.article and fact.term[:1].islower() and not _is_plural(fact.term) and not fact.term.endswith(("ing", "ism", "ity", "ness", "sis")):
            fact.article = _article_for(fact.term)
        if fact.plural and fact.verb == "is":
            fact.verb = "are"
        return fact

    # ---- per-sentence patterns ---------------------------------------------

    def _definitions(self, sentence: str, chunk, pages, topic) -> List[Fact]:
        facts: List[Fact] = []
        s = _normalize_for_matching(sentence)
        if len(s) < 12 or len(s) > 400:
            return facts

        # "X ..., whereas/while Y ..." holds two definitions.
        parts = re.split(r",\s+(?:whereas|while)\s+", s)
        if len(parts) == 2 and all(len(p.split()) >= 4 for p in parts):
            owner = re.search(r"\bof\s+((?:an?|the)\s+[a-z]+)\b", parts[0])
            if owner:
                parts[1] = re.sub(r"\b(?:is|are)\s+(its|their)\s", lambda mm: mm.group(0).replace(mm.group(1), f"{owner.group(1)}'s"), parts[1], count=1)
            for part in parts:
                part = _sentence_case(part)
                found = self._definitions(part, chunk, pages, topic)
                for f in found:
                    f.source = sentence
                facts.extend(found)
            if facts:
                return facts

        for pattern, kind in DEF_PATTERNS:
            m = pattern.match(s)
            if m:
                verb = m.group("verb")
                if kind == "refers":
                    verb = "refer" if verb.lower() == "refer to" else "is"
                fact = self._make_definition(chunk, pages, topic, sentence, m.group("term"), m.group("def"), verb=verb, article=m.groupdict().get("art") or "")
                if fact:
                    if " who " in f" {m.group('def')} " and fact.verb in {"was", "were"}:
                        raw = _strip_article(m.group("term"))
                        if len(raw.split()) == 1 and raw[:1].isupper():
                            fact.term = raw
                        fact.question = f"Who {fact.verb} {'the ' if fact.term[:1].isupper() and fact.plural else ''}{fact.term}?"
                    return [fact]

        m = CALLED_PATTERN.match(s)
        if m and not PRONOUN_START.match(m.group("def")):
            fact = self._make_definition(chunk, pages, topic, sentence, m.group("term"), m.group("def"))
            if fact:
                return [fact]

        m = COLON_PATTERN.match(s)
        if m and len(m.group("term").split()) <= 6:
            definition = m.group("def").strip()
            if COMPLEXITY_RE.match(definition):
                return facts
            if len(definition.split()) >= 3:
                fact = self._make_definition(chunk, pages, topic, sentence, m.group("term"), definition, colon=True, base=2.5)
                if fact:
                    return [fact]
        return facts

    def _special(self, sentence: str, chunk, pages, topic) -> List[Fact]:
        facts: List[Fact] = []
        s = _normalize_for_matching(sentence)

        m = LAW_PATTERN.match(s)
        if m:
            term = m.group("term").strip()
            article = ""
            if term.lower().startswith("the "):
                article, term = "the ", term[4:]
            facts.append(Fact("law", chunk.id, pages, topic, sentence, term=self.display_term(term), article=article,
                              definition=_end(_sentence_case(m.group("def"))), verb=m.group("verb"), score=4.0 + self.term_weight(term)))

        m = MEASURE_PATTERN.match(s)
        if m and _good_term(m.group("term")):
            term = m.group("term")
            article = (m.group("art") or "").lower()
            facts.append(Fact("measure", chunk.id, pages, topic, sentence, term=self.display_term(term),
                              article=f"{article} " if article else "", verb=m.group("verb"),
                              definition=_end(_sentence_case(m.group("def"))), score=3.5 + self.term_weight(term)))

        m = KNOWN_AS_PERSON.match(s)
        if m and not (set(m.group("who").lower().split()) & NON_PERSON_WORDS):
            self.persons.add(m.group("who"))
            facts.append(Fact("who", chunk.id, pages, topic, sentence, term=m.group("who"), answer=m.group("who"),
                              question=f"Who is known as {m.group('what').rstrip('.')}?", score=4.0))

        m = EXAMPLE_PATTERN.match(s)
        if m and _good_term(m.group("ex")) and _good_term(m.group("of")):
            of = m.group("of").strip()
            facts.append(Fact("example", chunk.id, pages, topic, sentence, term=of, answer=self.display_term(_strip_article(m.group("ex"))),
                              question=f"What is an example of {_article_for(of) if not _is_plural(of) else ''}{of}?", score=3.0))

        for pattern in (EVENT_ACTIVE, EVENT_PASSIVE):
            m = pattern.match(s)
            if not m:
                continue
            who = m.group("who")
            if set(who.lower().split()) & NON_PERSON_WORDS:
                continue
            self.persons.add(who)
            obj = m.group("obj").strip().rstrip(",")
            obj_l = _lower_first(obj) if obj.split()[0].lower() in {"the", "a", "an", "his", "her", "their"} else obj
            verb = m.group("verb")
            facts.append(Fact("who", chunk.id, pages, topic, sentence, term=who, answer=who,
                              question=f"Who {verb} {obj_l}?", score=4.5))
            year = m.groupdict().get("year") or m.groupdict().get("year1") or m.groupdict().get("year2")
            if year:
                facts.append(Fact("event", chunk.id, pages, topic, sentence, term=who, answer=year, year=year,
                                  question=f"In what year did {who} {PERSON_VERBS[verb]} {obj_l}?", score=4.0))
            break

        # Formulas attached to a named quantity or law.
        fm = FORMULA_RE.search(sentence)
        if fm and ("(" in sentence or "calculated as" in sentence or "given by" in sentence):
            formula = re.sub(r"\s+", " ", fm.group(1)).strip()
            named = None
            for f in facts:
                if f.kind == "law":
                    named = f"{f.article}{f.term}"
            if not named:
                dm = re.match(rf"^(?:The\s+)?({NOUN_PHRASE})\s+(?:is|are|equals)\s", s)
                if dm and _good_term(dm.group(1)):
                    named = self.display_term(_strip_article(dm.group(1)))
            if named:
                question = f"What equation expresses {named}?" if re.search(r"\b(law|principle|rule)\b", named, re.I) else f"What is the formula for {_lower_first(named) if not named[:1].isupper() or not self._capitalised_mid_sentence(named.split()[0]) else named}?"
                facts.append(Fact("formula", chunk.id, pages, topic, sentence, term=named, answer=formula, question=question, score=3.5))
        return facts

    @staticmethod
    def _heading_phrase(heading: str) -> str:
        return " ".join(w if ACRONYM_TOKEN.fullmatch(w) else w.lower() for w in heading.split())

    def _complexity(self, sentence: str, chunk, pages, topic) -> Optional[Fact]:
        m = re.match(r"^(?P<label>[A-Za-z][\w\s\-'()]{2,60}?)\s*:\s*(?P<value>O\([^)]{1,12}\))\s*$", sentence.strip())
        if not m:
            return None
        label = _lower_first(m.group("label").strip())
        value = m.group("value").replace(" ", " ")
        context = ""
        heading = topic or chunk.heading
        names_structure = bool(ACRONYM_TOKEN.search(m.group("label"))) or any(t in label for t in self._known_terms)
        if heading and not names_structure:
            context = f" for {self._heading_phrase(heading)}"
        return Fact("complexity", chunk.id, pages, topic, sentence, term=label, answer=value,
                    question=f"What is the time complexity of {label}{context}?", score=3.5)

    def _acronyms(self, text: str, sentences: List[str], chunk, pages, topic, seen: set) -> List[Fact]:
        facts = []
        for match in ACRONYM_PATTERN.finditer(display_text(text)):
            expansion, acronym = match.group(1).strip(), match.group(2).strip()
            initials = "".join(w[0] for w in re.split(r"[\s\-]+", expansion) if w)
            if acronym.rstrip("s").upper() not in initials.upper() or acronym.lower() in seen:
                continue
            seen.add(acronym.lower())
            sentence = next((s for s in sentences if acronym in s), f"{expansion} ({acronym})")
            facts.append(Fact("acronym", chunk.id, pages, topic, sentence, term=acronym, definition=expansion, score=2.5))
        return facts

    def _lists(self, text: str, chunk, pages, topic, seen: set) -> List[Fact]:
        facts: List[Fact] = []
        heading: Optional[str] = None
        lead: Optional[str] = None
        items: List[str] = []

        def close():
            nonlocal items, lead
            label = lead or heading
            usable = label and 2 <= len(items) <= 8 and all(len(i) <= 160 for i in items)
            if usable:
                ordered = all(re.match(r"^\d+\.\s", i) for i in items)
                short_items = all(":" not in i and len(i.split()) <= 7 for i in items)
                named_list = bool(LIST_LEAD.match(label)) or ordered or bool(lead)
                if named_list or short_items:
                    clean_items = [re.sub(r"^\d+\.\s", "", i) for i in items]
                    source = " ".join(items)
                    if source not in seen:
                        seen.add(source)
                        name = label.rstrip(":").strip()
                        name_l = _lower_first(name)
                        n = len(items)
                        if re.match(r"^(?:the\s+)?(?:steps|stages|phases)\b", name_l):
                            question = f"What are the {n} {name_l}?"
                        elif LIST_LEAD.match(name_l):
                            question = f"What are the {n} {re.sub(r'^the ', '', name_l)}?"
                        elif ordered:
                            question = f"What are the {n} steps of {name_l}?"
                        else:
                            question = f"List the {n} key points of {name_l}."
                        facts.append(Fact("list", chunk.id, pages, topic or heading, source, term=name, items=clean_items,
                                          ordered=ordered, question=question, score=2.5 + 0.2 * n))
            items = []
            lead = None

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("# "):
                close()
                heading = line[2:].strip()
                continue
            if line.startswith("•"):
                item = _clean(line.lstrip("•"))
                if item:
                    items.append(item)
                continue
            close()
            if line.endswith(":") and len(line.split()) <= 12:
                lead = line.rstrip(":")
                heading = None
        close()
        return facts

    # ---- main ---------------------------------------------------------------

    def extract(self) -> List[Fact]:
        facts: List[Fact] = []
        seen_terms: set = set()
        seen_sources: set = set()
        seen_questions: set = set()

        def keep(fact: Fact) -> bool:
            key = (fact.kind, (fact.question or fact.term).lower())
            if key in seen_questions:
                return False
            if fact.kind == "definition":
                if fact.term.lower() in seen_terms:
                    return False
                seen_terms.add(fact.term.lower())
            seen_questions.add(key)
            return True

        # Persons first, so later term display knows them.
        for chunk in self.chunks:
            for sentence in split_sentences(chunk.content):
                for m in (KNOWN_AS_PERSON.match(_normalize_for_matching(sentence)), EVENT_ACTIVE.match(_normalize_for_matching(sentence))):
                    if m and not (set(m.group("who").lower().split()) & NON_PERSON_WORDS):
                        self.persons.add(m.group("who"))

        # Terms defined anywhere (used to tell "search in a balanced BST" from "search").
        for chunk in self.chunks:
            for sentence in split_sentences(chunk.content):
                m = COLON_PATTERN.match(sentence) or DEF_PATTERNS[2][0].match(sentence)
                if m and _good_term(_strip_article(m.group("term"))):
                    self._known_terms.add(_strip_article(m.group("term")).lower())

        for chunk in self.chunks:
            pages = sorted({chunk.start_page, chunk.end_page})
            topic = chunk.heading
            sentences = [_clean(s) for s in split_sentences(chunk.content)]
            line_heading: Dict[str, Optional[str]] = {}
            current = chunk.heading
            for line in chunk.content.split("\n"):
                if line.startswith("# "):
                    current = line[2:].strip()
                    continue
                for piece in split_sentences(line):
                    line_heading.setdefault(_clean(piece), current)
            numbered = {s for s in sentences if re.match(r"^\d+\.\s", s)}

            for fact in self._acronyms(chunk.content, sentences, chunk, pages, topic, seen_terms):
                facts.append(fact)

            for sentence in sentences:
                found: List[Fact] = []
                complexity = self._complexity(sentence, chunk, pages, line_heading.get(sentence, topic))
                if complexity:
                    found.append(complexity)
                special = self._special(sentence, chunk, pages, topic)
                found.extend(special)
                if not any(f.kind in {"law", "measure", "example"} for f in special) and not any(f.kind == "who" and "known as" in f.question for f in special):
                    found.extend(self._definitions(sentence, chunk, pages, topic))
                for fact in found:
                    if keep(fact):
                        facts.append(fact)
                        seen_sources.add(sentence)

            facts.extend(self._lists(chunk.content, chunk, pages, topic, seen_sources))

            for sentence in sentences:
                if sentence in numbered or not _is_good_sentence(sentence) or CONTEXT_START.match(sentence):
                    continue
                if re.match(r"^[A-Za-z][\w\s\-'()]{1,50}:\s", sentence):
                    continue  # slide fragment, already handled above
                words = content_words(sentence)
                if len(words) < 3:
                    continue
                weight = sum(self.doc_terms.get(w, 0.0) for w in words)
                bonus = 0.0
                if re.search(r"\b(because|therefore|causes?|caused|results? in|leads? to|led to|consists? of|contains?|produces?|requires?|allows?|increases?|decreases?)\b", sentence, re.I):
                    bonus += 1.5
                if re.search(r"\b\d", sentence):
                    bonus += 1.0
                score = weight / math.sqrt(len(words)) + bonus
                anchored = bool(YEAR_RE.search(sentence) or re.search(r"(?<=[a-z,] )[A-Z][a-z]+", sentence)
                                or any(t in sentence.lower() for t in self._known_terms))
                if score < 0.8 and not anchored:
                    continue
                if anchored:
                    score = max(score, 1.2)
                facts.append(Fact("sentence", chunk.id, pages, topic, sentence, score=score))
        return facts


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

class LocalGenerator:
    def __init__(self, chunks: Sequence[ChunkInput], seed: int = 0):
        self.rng = random.Random(seed)
        self.extractor = FactExtractor(chunks)
        self.facts = self.extractor.extract()
        self.by_kind: Dict[str, List[Fact]] = {}
        for fact in self.facts:
            self.by_kind.setdefault(fact.kind, []).append(fact)
        self.definitions = [f for f in self.facts if f.kind in {"definition", "acronym"}]
        self.sentences = sorted(self.by_kind.get("sentence", []), key=lambda f: -f.score)
        self.used_targets: Counter = Counter()
        self.def_terms = {f.term.lower() for f in self.facts if f.kind in {"definition", "law", "measure"}}
        self.def_term_words = {w for t in self.def_terms for w in content_words(t)}
        self.heading_words = {w for h in self.extractor.headings for w in content_words(h)}
        self.term_pool = self._term_pool()

    # ---- vocabulary ---------------------------------------------------------

    def technicality(self, word: str) -> float:
        w = word.lower()
        if w in STOPWORDS or w in NOT_A_TERM or len(w) < 3:
            return -10.0
        if w.endswith(("ing", "ly")) or (w.endswith("ed") and not w.endswith("eed")):
            return -3.0
        score = min(len(w), 12) * 0.25
        if w in self.def_term_words or w.rstrip("s") in self.def_term_words:
            score += 4.0
        if w in self.heading_words:
            score += 1.5
        if w.endswith(TECH_SUFFIXES):
            score += 1.5
        tf = self.extractor.tf.get(w, 0)
        if tf <= 2:
            score += 1.0
        elif tf >= 8:
            score -= 1.5
        return score

    def _term_pool(self) -> List[str]:
        """Candidate answers and distractors: subject terms, never filler words."""
        pool: List[str] = []
        seen: set = set()

        def push(term: str):
            key = term.lower()
            if key not in seen and len(term) > 1:
                seen.add(key)
                pool.append(term)

        for fact in self.facts:
            if fact.kind in {"definition", "law", "measure"}:
                push(fact.term)
        text = self.extractor.all_text
        for token in ACRONYM_TOKEN.findall(text):
            if token not in {"I", "A", "AND", "OR", "THE"}:
                push(token)
        name_parts = {p.lower() for person in self.extractor.persons for p in person.split()}
        words = sorted(set(content_words(text)) - name_parts, key=lambda w: -self.technicality(w))
        for word in words[:150]:
            if self.technicality(word) >= 2.0:
                push(word)
        return pool

    @staticmethod
    def kind_of(answer: str, persons: Set[str]) -> str:
        a = answer.strip()
        if YEAR_RE.fullmatch(a):
            return "year"
        if re.fullmatch(r"\d{1,2}(?:st|nd|rd|th) century", a):
            return "century"
        if re.search(r"\b(law|principle|theorem)\b", a, re.I):
            return "law"
        if COMPLEXITY_RE.match(a):
            return "complexity"
        if re.fullmatch(r"\d+(?:[.,]\d+)?(?::\d+)?%?", a):
            return "number"
        if a in persons:
            return "person"
        if FORMULA_RE.fullmatch(a):
            return "formula"
        if len(a.split()) > 1:
            return "multi"
        if a[:1].isupper():
            return "proper"
        return "word"

    def _distractors(self, answer: str, k: int = 3, exclude_text: str = "") -> List[str]:
        """Wrong options of the same kind as the answer, never a word already in the question."""
        kind = self.kind_of(answer, self.extractor.persons)
        banned_text = (exclude_text or "").lower()
        answer_l = answer.lower()

        def allowed(t: str) -> bool:
            tl = t.lower()
            if tl == answer_l or tl in answer_l or answer_l in tl:
                return False
            return not re.search(rf"\b{re.escape(tl)}\b", banned_text)

        if kind == "year":
            y = int(answer)
            offsets = [o for o in (-31, -17, -11, -6, -3, 4, 8, 13, 19, 27) if 1000 <= y + o <= 2099]
            self.rng.shuffle(offsets)
            return [str(y + o) for o in offsets[:k]]
        if kind == "law":
            laws = [f.term for f in self.by_kind.get("law", []) if allowed(f.term)]
            self.rng.shuffle(laws)
            return laws[:k]
        if kind == "century":
            n = int(re.match(r"\d+", answer).group(0))

            def ordinal(v: int) -> str:
                suffix = "th" if 10 <= v % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(v % 10, "th")
                return f"{v}{suffix} century"
            return [ordinal(v) for v in (n - 1, n + 1, n - 2, n + 2) if v > 0][:k]
        if kind == "number":
            if ":" in answer:
                a, b = answer.split(":")
                options = {f"{b}:{a}", f"{int(a) + 1}:{b}", f"1:{a}", f"{a}:{int(b) + 1}"} - {answer}
                return list(options)[:k]
            value = float(answer.rstrip("%").replace(",", ""))
            pct = answer.endswith("%")
            out: List[str] = []
            for factor in (2, 0.5, 1.5, 3, 0.25):
                v = value * factor
                text = (f"{v:.0f}" if float(v).is_integer() or value.is_integer() else f"{v:.1f}") + ("%" if pct else "")
                if text != answer and text not in out:
                    out.append(text)
            return out[:k]
        if kind == "complexity":
            options = [o for o in ("O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)") if o.lower() != answer_l]
            self.rng.shuffle(options)
            return options[:k]
        if kind == "person":
            people = [p for p in self.extractor.persons if allowed(p)]
            self.rng.shuffle(people)
            return people[:k]
        if kind == "formula":
            others = [f.answer for f in self.by_kind.get("formula", []) if f.answer != answer]
            lhs, rhs = [p.strip() for p in answer.split("=", 1)]
            if len(rhs) == 2 and rhs.isalpha():
                others += [f"{lhs} = {rhs[0]}/{rhs[1]}", f"{lhs} = {rhs[1]}/{rhs[0]}", f"{lhs} = {rhs[0]} + {rhs[1]}"]
            seen_o: List[str] = []
            for o in others:
                if o not in seen_o:
                    seen_o.append(o)
            return seen_o[:k]

        multi = kind == "multi"
        capital = answer[:1].isupper()

        def fit(term: str) -> float:
            score = 0.0
            if (len(term.split()) > 1) == multi:
                score += 2
            if term[:1].isupper() == capital and answer.lower() not in self.def_terms:
                score += 1
            if term.lower() in self.def_terms:
                score += 3.0 if answer.lower() in self.def_terms else 1.5
            if re.search(r"\b(law|principle|theorem|rule)\b", term, re.I) and not re.search(r"\b(law|principle|theorem|rule)\b", answer, re.I):
                score -= 4
            score -= abs(len(term) - len(answer)) / 25
            return score + self.rng.random() * 0.8

        pool = [t for t in self.term_pool if allowed(t) and t not in self.extractor.persons]
        pool.sort(key=fit, reverse=True)
        picks = pool[:k]
        if capital and kind != "proper":
            picks = [p[:1].upper() + p[1:] for p in picks]
        return picks

    # ---- cloze --------------------------------------------------------------

    STRONG = 6.0
    MIN_CLOZE = 4.5

    def _cloze_target(self, sentence: str, remember: bool = True) -> Optional[str]:
        picked = self._cloze_pick(sentence, remember)
        return picked[0] if picked else None

    def _cloze_pick(self, sentence: str, remember: bool = True) -> Optional[tuple]:
        """Pick the most specific term in a sentence to blank out. Returns (term, strength)."""
        candidates: List[tuple] = []
        lower = sentence.lower()

        def repeats(term: str) -> bool:
            stem = term.lower()[:6]
            return len(re.findall(rf"\b{re.escape(stem)}", lower)) > 1

        for term in self.def_terms:
            if len(term) > 2 and re.search(rf"\b{re.escape(term)}\b", lower):
                candidates.append((9 + len(term.split()), self._original_case(sentence, term)))
        m = re.search(r"\b(?:called|termed)\s+(?:an?\s+|the\s+)?([a-z][\w\-]+(?:\s(?!of\b|and\b|or\b|in\b)[a-z][\w\-]+)?)", sentence)
        if m:
            candidates.append((11, m.group(1)))
        for person in self.extractor.persons:
            if person in sentence:
                candidates.append((9, person))
        for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+(?:of\s+)?[A-Z][a-z]+){1,3}\b", sentence):
            phrase = match.group(0)
            if match.start() > 0 and phrase.split()[0].lower() not in STOPWORDS:
                candidates.append((7 + self.extractor.term_weight(phrase), phrase))
        for token in ACRONYM_TOKEN.findall(sentence):
            if token not in {"I", "A", "SI"}:
                candidates.append((7.5, token))
        for match in re.finditer(r"(?<=[a-z,] )([A-Z][a-z]{3,})\b(?!\s+[A-Z])", sentence):
            word = match.group(1)
            if word.lower() not in STOPWORDS and not any(word in p for p in self.extractor.persons):
                candidates.append((6.5, word))
        for century in re.findall(r"\b\d{1,2}(?:st|nd|rd|th) century\b", sentence):
            candidates.append((7.5, century))
        for year in YEAR_RE.findall(sentence):
            candidates.append((7.5, year))
        for number in re.findall(r"(?<![\w.])(\d+:\d+|\d+(?:\.\d+)?%|\d{2,3}(?!\d))(?![\w.:])", sentence):
            if not YEAR_RE.fullmatch(number):
                candidates.append((6.5, number))
        for m2 in re.finditer(r"\b([a-z][a-z\-]{3,})\s+([a-z]+)\b", sentence):
            first, head = m2.group(1), m2.group(2)
            if head in HEAD_NOUNS and first not in STOPWORDS and first not in NOT_A_TERM and not first.endswith(("ed", "ly")):
                candidates.append((5.5 + 0.2 * len(first), f"{first} {head}"))
        for word in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", sentence):
            if any(word in c[1].split() for c in candidates if " " in c[1]):
                continue  # part of a longer term or name
            if word[:1].isupper() and sentence.find(word) > 0:
                continue  # part of a proper name handled above
            score = self.technicality(word)
            if score > 1.5:
                candidates.append((score, word))
        candidates = [(s, t) for s, t in candidates if not repeats(t) and t.lower() not in NOT_A_TERM]
        if not candidates:
            return None
        scored = [(score - 4.0 * self.used_targets[term.lower()], term, score) for score, term in candidates]
        scored.sort(key=lambda kv: -kv[0])
        _, best, strength = scored[0]
        if remember:
            self.used_targets[best.lower()] += 1
        return best, strength

    @staticmethod
    def _original_case(sentence: str, term: str) -> str:
        m = re.search(rf"\b{re.escape(term)}\b", sentence, re.I)
        return m.group(0) if m else term

    @staticmethod
    def _blank(sentence: str, target: str) -> str:
        return re.sub(rf"(?<![\w]){re.escape(target)}(?![\w])", "_____", sentence, count=1, flags=re.I)

    @staticmethod
    def _cloze_ok(blanked: str, original: str) -> bool:
        return blanked != original and len(blanked.replace("_____", "").split()) >= 4

    # ---- helpers ------------------------------------------------------------

    def _difficulty(self, fact: Fact, kind: str) -> int:
        base = {"definition": 2, "acronym": 2, "law": 3, "measure": 3, "who": 2, "event": 3, "example": 2,
                "formula": 3, "complexity": 3, "list": 4, "sentence": 3}.get(fact.kind, 3)
        if kind in {"cloze", "fill_blank", "short_answer"}:
            base += 1
        if len(fact.source.split()) > 28:
            base += 1
        return max(1, min(5, base))

    @staticmethod
    def _accept_difficulty(level: int, wanted: str) -> bool:
        if wanted == "easy":
            return level <= 3
        if wanted == "hard":
            return level >= 3
        return True

    @staticmethod
    def _meta(fact: Fact) -> dict:
        return {"chunk_id": fact.chunk_id, "pages": fact.pages, "source_quote": fact.source, "topic": fact.topic}

    def _definition_front(self, fact: Fact) -> str:
        if fact.question:
            return fact.question
        if fact.kind == "acronym":
            return f"What does {fact.term} stand for?"
        does = "do" if fact.plural else "does"
        if fact.colon and re.match(r"^[A-Z][a-z]+s\s", fact.definition) and not re.match(r"^(?:A|An|The|One|Two|Each|All)\s", fact.definition):
            return f"What {does} {fact.article}{fact.term} do?"
        verb = fact.verb if fact.verb in {"is", "are", "was", "were"} else ("are" if fact.plural else "is")
        if len(fact.term.split()) > 5:
            return f"Define: {fact.term}"
        return f"What {verb} {fact.article}{fact.term}?"

    def _qa_front(self, fact: Fact) -> str:
        if fact.kind == "law":
            verb_base = {"states": "state", "says": "say", "holds": "hold", "predicts": "predict", "proposes": "propose", "shows": "show"}.get(fact.verb, "state")
            return f"What does {fact.article}{fact.term} {verb_base}?"
        if fact.kind == "measure":
            verb_base = fact.verb[:-1] if fact.verb.endswith("s") else fact.verb
            return f"What does {fact.article}{fact.term} {verb_base}?"
        return fact.question

    # ---- flashcards ---------------------------------------------------------

    def generate_cards(self, count: int, card_types: Sequence[str], difficulty: str = "mixed") -> List[dict]:
        types = {t.lower() for t in card_types} or {"basic", "cloze"}
        if "definition" in types or "concept" in types:
            types.add("basic")
        cards: List[dict] = []
        used_sources: Counter = Counter()

        limit = {"value": 1}

        def add(card: dict, fact: Fact):
            if used_sources[fact.source] >= limit["value"]:
                return
            if any(c["front"] == card["front"] for c in cards):
                return
            if not self._accept_difficulty(card["difficulty"], difficulty):
                return
            used_sources[fact.source] += 1
            cards.append({**self._meta(fact), **card})

        basic: List[tuple] = []
        for fact in sorted(self.facts, key=lambda f: -f.score):
            if fact.kind in {"definition", "acronym"}:
                basic.append((fact, {"card_type": "definition", "front": self._definition_front(fact),
                                     "back": fact.answer or (fact.definition if fact.kind != "acronym" else fact.definition),
                                     "difficulty": self._difficulty(fact, "basic"),
                                     "extra_explanation": fact.source if fact.source.rstrip(".") != fact.definition.rstrip(".") else None}))
            elif fact.kind in {"law", "measure"}:
                basic.append((fact, {"card_type": "concept", "front": self._qa_front(fact), "back": fact.definition,
                                     "difficulty": self._difficulty(fact, "basic")}))
            elif fact.kind in {"who", "event", "example", "complexity"}:
                basic.append((fact, {"card_type": "basic", "front": fact.question, "back": fact.answer,
                                     "difficulty": self._difficulty(fact, "basic"), "extra_explanation": fact.source}))
            elif fact.kind == "formula":
                basic.append((fact, {"card_type": "formula", "front": fact.question, "back": fact.answer,
                                     "difficulty": self._difficulty(fact, "basic"), "extra_explanation": fact.source}))
            elif fact.kind == "list":
                back = "\n".join(f"{i}. {item}" for i, item in enumerate(fact.items, 1)) if fact.ordered else "\n".join(f"• {item}" for item in fact.items)
                basic.append((fact, {"card_type": "process" if fact.ordered else "concept", "front": fact.question, "back": back,
                                     "difficulty": self._difficulty(fact, "basic")}))

        reverse: List[tuple] = []
        for fact in self.by_kind.get("definition", []):
            reverse.append((fact, {"card_type": "definition", "front": f"Which term matches this description? {_trim(fact.definition, 240)}",
                                   "back": fact.term, "difficulty": self._difficulty(fact, "reverse") + 1}))

        cloze: List[tuple] = []
        cloze_sources: List[Fact] = []
        seen_cloze: set = set()
        for fact in self.sentences + [f for f in self.by_kind.get("definition", []) if not f.colon]:
            if fact.source not in seen_cloze:
                seen_cloze.add(fact.source)
                cloze_sources.append(fact)
        for fact in cloze_sources:
            picked = self._cloze_pick(fact.source)
            if not picked or picked[1] < self.MIN_CLOZE:
                continue
            target = picked[0]
            blanked = self._blank(fact.source, target)
            if not self._cloze_ok(blanked, fact.source):
                continue
            cloze.append((fact, {"card_type": "cloze", "front": _end(blanked), "back": target, "cloze_text": _end(blanked),
                                 "cloze_answer": target, "extra_explanation": fact.source,
                                 "difficulty": self._difficulty(fact, "cloze")}))

        queues = []
        if "basic" in types:
            queues.append(basic)
        if "cloze" in types:
            queues.append(cloze)
        if "reverse" in types:
            queues.append(reverse)
        if not queues:
            queues = [basic, cloze]
        index = [0] * len(queues)
        while len(cards) < count and any(index[i] < len(q) for i, q in enumerate(queues)):
            for i, queue in enumerate(queues):
                if index[i] < len(queue) and len(cards) < count:
                    fact, card = queue[index[i]]
                    index[i] += 1
                    add(card, fact)
        if len(cards) < count:
            limit["value"] = 3
            for fact, card in basic + cloze:
                if len(cards) >= count:
                    break
                add(card, fact)
        return cards[:count]

    # ---- quizzes ------------------------------------------------------------

    def generate_questions(self, count: int, question_types: Sequence[str], difficulty: str = "mixed") -> List[dict]:
        types = [t for t in question_types if t in {"mcq", "true_false", "fill_blank", "short_answer"}] or ["mcq", "true_false", "fill_blank"]
        builders = {"mcq": self._mcq, "true_false": self._true_false, "fill_blank": self._fill_blank, "short_answer": self._short_answer}
        pools = {t: builders[t]() for t in types}
        for pool in pools.values():
            self.rng.shuffle(pool)
            pool.sort(key=lambda q: -q.pop("_score", 0))

        questions: List[dict] = []
        used: Counter = Counter()
        while len(questions) < count and any(pools.values()):
            for t in types:
                pool = pools[t]
                while pool:
                    q = pool.pop(0)
                    if used[q["source_quote"]] >= 1 and any(p for p in pools.values()):
                        continue
                    if not self._accept_difficulty(q["difficulty"], difficulty):
                        continue
                    used[q["source_quote"]] += 1
                    questions.append(q)
                    break
                if len(questions) >= count:
                    break
        return questions

    def _options(self, correct: str, wrong: Sequence[str]) -> tuple:
        texts = [correct, *wrong]
        self.rng.shuffle(texts)
        options = [{"id": "abcdefgh"[i], "text": text} for i, text in enumerate(texts)]
        return options, next(o["id"] for o in options if o["text"] == correct)

    def _question(self, fact: Fact, qtype: str, text: str, answer: str, explanation: str, difficulty: int, score: float, options=None) -> dict:
        if options is None and qtype == "true_false":
            options = [{"id": "true", "text": "True"}, {"id": "false", "text": "False"}]
        return {**self._meta(fact), "question_type": qtype, "question_text": text, "options": options,
                "correct_answer": answer, "explanation": explanation, "difficulty": difficulty, "_score": score}

    def _mcq(self) -> List[dict]:
        out: List[dict] = []
        defs = [f for f in self.by_kind.get("definition", [])]
        for fact in self.facts:
            if fact.kind == "acronym":
                wrong = [f.definition for f in self.by_kind.get("acronym", []) if f is not fact][:3]
                if len(wrong) == 3:
                    options, answer = self._options(fact.definition, wrong)
                    out.append(self._question(fact, "mcq", f"What does {fact.term} stand for?", answer, f"{fact.term} stands for {fact.definition}.", 2, fact.score, options))
            elif fact.kind == "definition":
                others = [f.definition for f in defs if f is not fact]
                if len(others) >= 3 and self.rng.random() < 0.5:
                    wrong = self.rng.sample(others, 3)
                    options, answer = self._options(_trim(fact.definition, 200), [_trim(w, 200) for w in wrong])
                    text = f"Which statement best describes {fact.article}{fact.term}?"
                else:
                    wrong = self._distractors(fact.term, 3, exclude_text=fact.definition)
                    if len(wrong) < 3:
                        continue
                    options, answer = self._options(fact.term, wrong)
                    text = f"Which term is described here? “{_trim(fact.definition, 240)}”"
                out.append(self._question(fact, "mcq", text, answer, _end(fact.source), self._difficulty(fact, "mcq"), fact.score, options))
            elif fact.kind in {"who", "event", "example", "complexity", "formula"}:
                wrong = self._distractors(fact.answer, 3, exclude_text=fact.question)
                if len(wrong) == 3:
                    options, answer = self._options(fact.answer, wrong)
                    out.append(self._question(fact, "mcq", fact.question, answer, _end(fact.source), self._difficulty(fact, "mcq"), fact.score, options))
            elif fact.kind == "law":
                laws = [f for f in self.by_kind.get("law", []) if f is not fact]
                if len(laws) >= 2:
                    wrong = [f"{f.article}{f.term}" for f in laws][:3]
                    correct = f"{fact.article}{fact.term}"
                    options, answer = self._options(_sentence_case(correct), [_sentence_case(w) for w in wrong])
                    statement = _lower_first(fact.definition).rstrip(".")
                    out.append(self._question(fact, "mcq", f"Which of these states that {statement}?", answer, _end(fact.source), 3, fact.score, options))
        for fact in self.sentences:
            picked = self._cloze_pick(fact.source)
            if not picked or picked[1] < self.STRONG:
                continue
            target = picked[0]
            blanked = self._blank(fact.source, target)
            if not self._cloze_ok(blanked, fact.source):
                continue
            wrong = self._distractors(target, 3, exclude_text=fact.source)
            if len(wrong) < 3:
                continue
            options, answer = self._options(target, wrong)
            out.append(self._question(fact, "mcq", f"Choose the word or phrase that completes the statement: “{_end(blanked)}”", answer,
                                      _end(fact.source), self._difficulty(fact, "mcq"), fact.score * 0.8, options))
        return out

    def _true_false(self) -> List[dict]:
        out: List[dict] = []
        defs = self.by_kind.get("definition", [])
        laws = self.by_kind.get("law", [])
        candidates = [f for f in self.sentences if len(f.source.split()) <= 35] + defs + laws + self.by_kind.get("who", [])
        for fact in candidates:
            truth = True
            statement = _end(fact.source)
            if fact.kind == "definition" and fact.colon and re.match(r"^(?:a|an|the|one)\s", fact.definition, re.I):
                verb = "are" if fact.plural else "is"
                statement = _end(f"{_sentence_case(fact.article + fact.term)} {verb} {_lower_first(fact.definition)}")
            elif fact.kind == "definition" and fact.colon and re.match(r"^[A-Z][a-z]+s\s", fact.definition) and fact.article:
                statement = _end(f"{_sentence_case(fact.article + fact.term)} {_lower_first(fact.definition)}")
            if self.rng.random() < 0.5:
                if fact.kind == "definition" and len(defs) >= 2:
                    def noun_phrase(d: Fact) -> bool:
                        return bool(re.match(r"^(?:a|an|the|one|any)\s", d.definition, re.I))
                    others = [d for d in defs if d is not fact and noun_phrase(d) == noun_phrase(fact) and d.plural == fact.plural]
                    if others and noun_phrase(fact):
                        other = self.rng.choice(others)
                        verb = "are" if fact.plural else "is"
                        statement = _end(f"{_sentence_case(fact.article + fact.term)} {verb} {_lower_first(other.definition)}")
                        truth = False
                elif fact.kind == "law" and len(laws) >= 2:
                    other = self.rng.choice([l for l in laws if l is not fact])
                    statement = _end(f"{_sentence_case(fact.article + fact.term)} {fact.verb} that {_lower_first(other.definition)}")
                    truth = False
                else:
                    picked = self._cloze_pick(fact.source, remember=False)
                    target = picked[0] if picked and picked[1] >= self.STRONG else None
                    swap = self._distractors(target, 1, exclude_text=fact.source) if target else []
                    if target and swap:
                        replacement = swap[0] if target[:1].isupper() else _lower_first(swap[0])
                        altered = _end(_fix_articles(_sentence_case(re.sub(rf"(?<![\w]){re.escape(target)}(?![\w])", replacement, fact.source, count=1))))
                        if altered != statement:
                            statement, truth = altered, False
            explanation = ("True. " + _end(fact.source)) if truth else ("False. Your notes say: " + _end(fact.source))
            out.append(self._question(fact, "true_false", f"True or false: {statement}", "true" if truth else "false", explanation,
                                      max(1, self._difficulty(fact, "tf") - 1), fact.score * 0.7))
        return out

    def _fill_blank(self) -> List[dict]:
        out: List[dict] = []
        for fact in self.sentences + [f for f in self.by_kind.get("definition", [])] + self.by_kind.get("who", []):
            if fact.kind == "definition" and fact.colon:
                verb_start = re.match(r"^[A-Z][a-z]+s\s", fact.definition) and not re.match(r"^(?:A|An|The|One|Two|Each|All)\s", fact.definition)
                text = f"_____ {_lower_first(fact.definition)}" if verb_start else f"_____: {_lower_first(fact.definition)}"
                out.append(self._question(fact, "fill_blank", f"Fill in the blank: {text}", fact.term, _end(fact.source),
                                          self._difficulty(fact, "fill_blank"), fact.score * 0.75))
                continue
            if fact.kind == "who":
                target = fact.answer if fact.answer in fact.source else None
            else:
                picked = self._cloze_pick(fact.source)
                target = picked[0] if picked and picked[1] >= self.MIN_CLOZE else None
            if not target or len(target) > 40:
                continue
            blanked = self._blank(fact.source, target)
            if not self._cloze_ok(blanked, fact.source):
                continue
            out.append(self._question(fact, "fill_blank", f"Fill in the blank: {_end(blanked)}", target, _end(fact.source),
                                      self._difficulty(fact, "fill_blank"), fact.score * 0.75))
        return out

    def _short_answer(self) -> List[dict]:
        out: List[dict] = []
        for fact in self.facts:
            if fact.kind == "acronym":
                out.append(self._question(fact, "short_answer", f"What does {fact.term} stand for?", fact.definition, _end(fact.source), 2, fact.score))
            elif fact.kind == "definition":
                out.append(self._question(fact, "short_answer", f"Name the term: {_trim(fact.definition, 240)}", fact.term, _end(fact.source),
                                          self._difficulty(fact, "short_answer"), fact.score))
            elif fact.kind in {"who", "event", "example", "complexity", "formula"}:
                out.append(self._question(fact, "short_answer", fact.question, fact.answer, _end(fact.source),
                                          self._difficulty(fact, "short_answer"), fact.score))
            elif fact.kind == "list":
                out.append(self._question(fact, "short_answer", fact.question, "; ".join(fact.items), "Key points: " + "; ".join(fact.items), 4, fact.score * 0.6))
        return out
