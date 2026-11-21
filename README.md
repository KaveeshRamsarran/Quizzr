# Quizzr

Quizzr turns lecture PDFs into flashcards, quizzes and a spaced-repetition review schedule.

Upload a PDF, and Quizzr reads it and splits it into study sections. From there you can make a deck or a quiz, study the cards that are due each day, and track your progress. Cards and questions are written on your own computer: no API keys, nothing sent to a cloud service. Each one keeps the sentence and page it came from.

## Features

- **PDF reading:** text extraction with header and footer cleanup, heading detection and section chunking. OCR for scanned pages runs when Tesseract is installed (it is in the Docker image).
- **Flashcards:** definition, key-point, cloze and reverse cards. You can edit, add, delete and search cards, and export a deck as CSV or as an Anki import file.
- **Quizzes:** multiple choice, true or false, fill in the blank and short answer, with an optional time limit. Feedback is given per question, and results are broken down by topic. Short-answer grading tolerates typos.
- **Spaced repetition:** SM-2 scheduling. Each session shows due cards first, then cards you haven't studied. A card rated Again comes back before the session ends.
- **Progress:** streaks, study time, daily activity, card mastery, quiz topics (weakest first) and the questions you miss most.
- **Accounts:** email and password, guest accounts that can be upgraded later, profile, password change and account deletion.
- **Light and dark mode.**

### How the cards are made

The built-in generator (`backend/app/services/local_generator.py`) runs offline and finishes in a second or two. It builds study items from:

- **definitions:** "X is a...", "X refers to...", "... is called X", "X: ..."
- **acronyms:** "Adenosine Triphosphate (ATP)"
- **bulleted lists** under a heading
- **key sentences:** the ones carrying the document's most important terms, used for fill-the-gap cards, true or false and fill in the blank

It also recognises laws ("The law of X states that..."), people and dates ("James Watt improved the steam engine in 1769"), examples, formulas such as F = ma, time complexities on slides ("Search: O(n)") and numbered steps. Multiple-choice distractors are of the same kind as the answer: other terms, other people, nearby years, other complexities. Because every item is built from a real sentence in your notes, nothing is invented. Documents written in full sentences give the most cards; slides with only fragments give fewer.

## Run it

### Windows, one click

Double-click `start-servers.bat`. The first run creates the Python environment and installs packages. After that it starts both servers and opens http://localhost:3000.

### Manually

Requirements: Python 3.11 or later, and Node 18 or later.

```bash
# API (http://127.0.0.1:8002, docs at /docs)
cd backend
python -m venv .venv
.venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8002

# Web app (http://localhost:3000), in a second terminal
cd frontend
npm install
npm run dev
```

There is no Redis, worker or database server to run. Uploads and generation run as background jobs inside the API process, and data lives in `backend/quizzr.db` (SQLite).

### Single server or Docker

Run `npm run build` in `frontend/`. The API then serves the built app at http://127.0.0.1:8002.

`docker compose up --build` runs the same single server against PostgreSQL, with OCR included.

## Configuration

Copy `.env.example` to `.env` (in the repo root or in `backend/`). Every setting is optional. If `SECRET_KEY` is not set, a random key is generated and stored in `backend/.secret_key`.

## Project layout

```
backend/
  app/
    models/       SQLAlchemy models (documents, decks, cards, quizzes, review log...)
    routers/      FastAPI routes under /api/v1
    schemas/      Pydantic request and response models
    services/
      pdf_processing.py   extraction, cleanup, chunking
      local_generator.py  the built-in card and question generator
      generation.py       deck and quiz generation
      jobs.py             in-process background jobs
      analytics.py, spaced_repetition.py, quiz.py, deck.py, auth.py
  tests/          pytest suite (pytest -q)
frontend/
  src/
    pages/        screens (Today, Documents, Decks, Study, Quizzes, Progress, Settings...)
    components/   layout, dialogs, shared controls
    lib/          API client, formatting, theme
    styles/       design tokens
```

## Sample lectures

`samples/lectures/` holds five short lecture PDFs in different styles (biology notes, a history lecture, CS slides, an economics textbook chapter, a physics lecture) to try the app with. `samples/make_lectures.py` rebuilds them, and `samples/evaluate.py` prints every card and question the generator makes from them:

```bash
backend/.venv/Scripts/python samples/evaluate.py            # all five
backend/.venv/Scripts/python samples/evaluate.py hist110    # one
```

## Tests

```bash
cd backend && pytest -q
cd frontend && npm run lint && npm run build
```

## License

MIT
