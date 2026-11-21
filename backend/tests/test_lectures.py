"""Quality tests for the built-in generator on the five sample lectures (samples/make_lectures.py)."""

import importlib.util
import os
import re

import pytest

from app.services import pdf_processing
from app.services.local_generator import NOT_A_TERM, ChunkInput, LocalGenerator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_lectures_module():
    spec = importlib.util.spec_from_file_location("make_lectures", os.path.join(ROOT, "samples", "make_lectures.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    module = _make_lectures_module()
    folder = tmp_path_factory.mktemp("lectures")
    results = {}
    for name, (header, pages) in module.LECTURES.items():
        path = folder / name
        module.write_pdf(str(path), header, pages)
        cleaned = pdf_processing.clean_pages(pdf_processing.extract_pdf_pages(str(path)))
        style, _ = pdf_processing.analyze_document_structure(cleaned)
        chunks = pdf_processing.create_chunks(cleaned, style)
        inputs = [ChunkInput(i, c["content"], c["start_page"], c["end_page"], c.get("heading_context")) for i, c in enumerate(chunks)]
        cards = LocalGenerator(inputs, seed=1).generate_cards(40, ["basic", "cloze"])
        questions = LocalGenerator(inputs, seed=1).generate_questions(25, ["mcq", "true_false", "fill_blank", "short_answer"])
        results[name.split("-")[0]] = (cards, questions)
    return results


def card(cards, front):
    match = [c for c in cards if c["front"] == front]
    assert match, f"missing card {front!r}; have {[c['front'] for c in cards]}"
    return match[0]


def test_biology(generated):
    cards, _ = generated["bio201"]
    assert card(cards, "What is an allele?")["back"] == "A variant form of a gene."
    assert card(cards, "Who is known as the father of modern genetics?")["back"] == "Gregor Mendel"
    assert card(cards, "What does the law of segregation state?")["back"].startswith("The two alleles")
    assert "organism's" in card(cards, "What is the phenotype?")["back"]
    assert card(cards, "What are mutagens?")["back"].startswith("Agents")


def test_history(generated):
    cards, questions = generated["hist110"]
    assert card(cards, "Who invented the spinning jenny?")["back"] == "James Hargreaves"
    assert card(cards, "In what year did James Watt improve the steam engine?")["back"] == "1769"
    assert card(cards, "Who were the Luddites?")["back"].startswith("Textile workers")
    for q in questions:
        if q["question_type"] == "mcq" and q["question_text"].startswith("In what year"):
            years = [int(o["text"]) for o in q["options"]]
            assert max(years) - min(years) < 80


def test_slides(generated):
    cards, _ = generated["cs220"]
    assert card(cards, "What is the time complexity of search in a balanced BST?")["back"] == "O(log n)"
    assert card(cards, "What is the time complexity of search for linked lists?")["back"] == "O(n)"
    assert card(cards, "What does a hash function do?")["back"] == "Converts a key into an array index."
    assert card(cards, "What is an array?")


def test_economics(generated):
    cards, _ = generated["econ101"]
    assert card(cards, "What does price elasticity of demand measure?")["back"].startswith("How much")
    assert card(cards, "What is an example of a price ceiling?")["back"].lower() == "rent control"
    assert card(cards, "What are substitutes?")
    assert card(cards, "What does the law of demand state?")


def test_physics(generated):
    cards, _ = generated["phys101"]
    assert card(cards, "What is the formula for weight?")["back"] == "W = mg"
    steps = card(cards, "What are the 4 steps for solving a force problem?")["back"]
    assert steps.startswith("1. Draw a free-body diagram")
    assert card(cards, "What does Newton's third law state?")


def test_quality_invariants(generated):
    for name, (cards, questions) in generated.items():
        for c in cards:
            assert not re.match(r"^What (is|are) (When|If|Because|The|A|An)\b", c["front"]), (name, c["front"])
            if c["card_type"] == "cloze":
                assert c["back"].lower() not in NOT_A_TERM, (name, c["front"], c["back"])
                assert c["front"].count("_____") == 1
        for q in questions:
            text = q["question_text"]
            assert not re.search(r"\ba [aeiou]\w{2,}", text.lower()) or "a uniform" in text.lower() or "a one" in text.lower(), (name, text)
            if q["options"]:
                texts = [o["text"] for o in q["options"]]
                assert len(set(texts)) == len(texts), (name, text, texts)
                assert q["correct_answer"] in {o["id"] for o in q["options"]}
