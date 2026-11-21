"""
Runs Quizzr's PDF pipeline and built-in generator on the sample lectures and
prints every section, card and question, for judging generation quality.

Run from the repo root:
  backend/.venv/Scripts/python samples/evaluate.py              # all lectures
  backend/.venv/Scripts/python samples/evaluate.py phys101      # names containing "phys101"
  backend/.venv/Scripts/python samples/evaluate.py --cards 40 --questions 20
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.services import pdf_processing  # noqa: E402
from app.services.local_generator import ChunkInput, LocalGenerator  # noqa: E402


def load(path: str):
    raw = pdf_processing.extract_pdf_pages(path)
    pages = pdf_processing.clean_pages(raw)
    style, _ = pdf_processing.analyze_document_structure(pages)
    chunks = pdf_processing.create_chunks(pages, style)
    inputs = [ChunkInput(i, c["content"], c["start_page"], c["end_page"], c.get("heading_context")) for i, c in enumerate(chunks)]
    return style, chunks, inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("match", nargs="?", default="")
    parser.add_argument("--cards", type=int, default=30)
    parser.add_argument("--questions", type=int, default=15)
    parser.add_argument("--sections", action="store_true", help="also print the study sections")
    args = parser.parse_args()

    folder = os.path.join(HERE, "lectures")
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".pdf") or args.match not in name:
            continue
        style, chunks, inputs = load(os.path.join(folder, name))
        gen = LocalGenerator(inputs, seed=1)
        cards = gen.generate_cards(args.cards, ["basic", "cloze"])
        gen_q = LocalGenerator(inputs, seed=1)
        questions = gen_q.generate_questions(args.questions, ["mcq", "true_false", "fill_blank", "short_answer"])

        print("=" * 100)
        print(f"{name}  style={style.value}  sections={len(chunks)}  facts={Counter(f.kind for f in gen.facts)}")
        if args.sections:
            for c in chunks:
                print(f"  [p{c['start_page']}-{c['end_page']}] {c.get('heading_context')!r}  terms={c['key_terms'][:6]}")
        print(f"-- {len(cards)} cards")
        for c in cards:
            print(f"  [{c['card_type']:<10}] {c['front']}\n  {'':12} -> {c['back'][:110]}")
        print(f"-- {len(questions)} questions")
        for q in questions:
            opts = " | ".join(o["text"][:38] for o in (q.get("options") or []))
            print(f"  [{q['question_type']:<12}] {q['question_text'][:150]}")
            if opts:
                print(f"  {'':14} options: {opts}")
            print(f"  {'':14} answer: {q['correct_answer']}")


if __name__ == "__main__":
    main()
