"""End-to-end tests for PDF processing and the built-in generator."""

import textwrap

import pytest
from httpx import AsyncClient

from app.services.local_generator import ChunkInput, LocalGenerator

NOTES = [
    [
        "Cell Biology", "",
        "The Cell Membrane",
        "The cell membrane is a thin, flexible barrier that separates the interior of the cell from its environment.",
        "Diffusion is the net movement of particles from an area of high concentration to an area of low concentration.",
        "Osmosis refers to the diffusion of water across a selectively permeable membrane.",
        "Active transport requires energy in the form of ATP because it moves substances against their gradient.",
    ],
    [
        "Organelles", "",
        "The mitochondrion is the organelle that produces most of the cell's ATP through cellular respiration.",
        "Ribosomes are the sites of protein synthesis in all living cells.",
        "The process by which cells break down glucose to release energy is called cellular respiration.",
        "The endoplasmic reticulum (ER) is a network of membranes that transports proteins and lipids.",
        "Adenosine Triphosphate (ATP) is the main energy currency of the cell.",
    ],
]


def make_pdf(pages) -> bytes:
    """Build a small text PDF without third-party libraries."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objs = []
    font = len(objs) + 1
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_id = 1 + 2 * len(pages) + 1
    kids = []
    for lines in pages:
        y, ops = 760, ["BT", "/F1 11 Tf"]
        for line in lines:
            for part in textwrap.wrap(line, 95) or [""]:
                ops.append(f"1 0 0 1 56 {y} Tm ({esc(part)}) Tj")
                y -= 16
        ops.append("ET")
        stream = "\n".join(ops)
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content_id = len(objs)
        objs.append(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R /Resources << /Font << /F1 {font} 0 R >> >> >>")
        kids.append(len(objs))
    objs.append(f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>")
    objs.append(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {len(objs)} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_local_generator_grounds_every_item():
    chunks = [ChunkInput(i, "\n".join(p), i + 1, i + 1, p[0]) for i, p in enumerate(NOTES)]
    gen = LocalGenerator(chunks, seed=1)
    source = " ".join(" ".join(p) for p in NOTES)

    cards = gen.generate_cards(12, ["basic", "cloze"])
    assert len(cards) >= 8
    fronts = {c["front"] for c in cards}
    assert "What is osmosis?" in fronts
    assert "What are ribosomes?" in fronts
    assert any(c["card_type"] == "cloze" and "_____" in c["front"] for c in cards)
    for card in cards:
        assert card["source_quote"] in source

    questions = gen.generate_questions(10, ["mcq", "true_false", "fill_blank", "short_answer"])
    assert len(questions) >= 6
    for q in questions:
        if q["question_type"] == "mcq":
            ids = {o["id"] for o in q["options"]}
            assert q["correct_answer"] in ids and len(ids) >= 3
        if q["question_type"] == "true_false":
            assert q["correct_answer"] in {"true", "false"}


@pytest.mark.asyncio
async def test_upload_generate_study_and_quiz(client: AsyncClient, authenticated_user: dict):
    h = authenticated_user["headers"]
    r = await client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", make_pdf(NOTES), "application/pdf")}, headers=h)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "processed", doc

    detail = (await client.get(f"/api/v1/documents/{doc['id']}", headers=h)).json()
    assert detail["page_count"] == 2 and detail["chunks"]

    r = await client.post("/api/v1/generation/deck", json={"document_id": doc["id"], "card_count": 10}, headers=h)
    assert r.status_code == 202, r.text
    job = (await client.get(f"/api/v1/generation/job/{r.json()['job_id']}", headers=h)).json()
    assert job["status"] == "completed", job
    deck_id = job["result_id"]

    deck = (await client.get(f"/api/v1/decks/{deck_id}", headers=h)).json()
    assert deck["card_count"] >= 5 and deck["new_count"] == deck["card_count"]

    # A brand-new deck must offer its cards for study.
    cards = (await client.get(f"/api/v1/decks/{deck_id}/study", headers=h)).json()
    assert len(cards) == deck["card_count"]
    r = await client.post(f"/api/v1/decks/{deck_id}/cards/{cards[0]['id']}/review", json={"rating": "good", "time_spent_ms": 4000}, headers=h)
    assert r.status_code == 200

    r = await client.post("/api/v1/generation/quiz", json={"document_id": doc["id"], "question_count": 5}, headers=h)
    job = (await client.get(f"/api/v1/generation/job/{r.json()['job_id']}", headers=h)).json()
    assert job["status"] == "completed", job
    quiz = (await client.get(f"/api/v1/quizzes/{job['result_id']}", headers=h)).json()
    attempt = (await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=h)).json()
    for q in quiz["questions"]:
        r = await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts/{attempt['id']}/answers", json={"question_id": q["id"], "answer": q["correct_answer"]}, headers=h)
        body = r.json()
        assert body["is_correct"], q
        # The client marks the right option from this, so it must always be sent.
        assert body["correct_answer"] == q["correct_answer"], body
    result = (await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts/{attempt['id']}/finish", headers=h)).json()
    assert result["percentage"] == 100 and result["passed"]

    overview = (await client.get("/api/v1/analytics/overview", headers=h)).json()
    assert overview["study_streak"] == 1 and overview["cards_studied_today"] == 1
    assert (await client.get("/api/v1/analytics/suggestions", headers=h)).status_code == 200
    assert (await client.get(f"/api/v1/decks/{deck_id}/export/anki", headers=h)).status_code == 200


@pytest.mark.asyncio
async def test_rejects_non_pdf(client: AsyncClient, authenticated_user: dict):
    r = await client.post("/api/v1/documents/upload", files={"file": ("notes.pdf", b"hello", "application/pdf")}, headers=authenticated_user["headers"])
    assert r.status_code == 400
