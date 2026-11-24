# Quizzr

Quizzr turns lecture PDFs into flashcards, quizzes and a spaced-repetition review schedule.

Upload a PDF, and Quizzr reads it and splits it into study sections. From there you can make a deck or a quiz, study the cards that are due each day, and track your progress. Cards and questions are written on your own computer: no API keys, nothing sent to a cloud service. Each one keeps the sentence and page it came from.

## Features

- **PDF reading:** text extraction with header and footer cleanup, heading detection and section chunking. OCR for scanned pages runs when Tesseract is installed (it is in the Docker image).
- **Flashcards:** definition, key-point, cloze and reverse cards. You can edit, add, delete and search cards, and export a deck as CSV or as an Anki import file.
- **Quizzes:** multiple choice, true or false, fill in the blank and short answer, with an optional time limit. Feedback is given per question, and results are broken down by topic. Short-answer grading tolerates typos.
- **Spaced repetition:** SM-2 scheduling. Each session shows due cards first, then cards you haven't studied. A card rated Again comes back before the session ends.
- **Progress:** streaks, study time, daily activity, card mastery, quiz topics (weakest first) and the questions you miss most.
- **Accounts:** sign-up with email confirmation, sign-in, password reset by email, optional Google or GitHub sign-in, guest accounts that can be upgraded later without losing work, profile, password change and account deletion. Handled by Supabase Auth when it is configured, and by Quizzr's own email and password accounts otherwise.
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

## Deploying with Supabase

Supabase can host both the database and sign-in. With `SUPABASE_URL` and `SUPABASE_ANON_KEY` set, the web app signs people in through Supabase Auth and the API accepts only Supabase tokens. Each Supabase user gets a Quizzr profile the first time they sign in. Without those two settings, Quizzr keeps using its own accounts, so local use still needs no setup.

1. **Keys.** In Project Settings > API Keys, copy the project URL into `SUPABASE_URL` and the anon (or publishable) key into `SUPABASE_ANON_KEY`. The anon key is public by design; the app sends it to the browser. Put the service_role (or secret) key in `SUPABASE_SERVICE_ROLE_KEY`. It is only ever used on the server, so never expose it. With it set:
   - Uploaded PDFs are stored in Supabase Storage. Quizzr creates a private `documents` bucket on startup, or the bucket named in `SUPABASE_STORAGE_BUCKET`. Only the server can read the bucket, and it streams each file to its owner. Without this key, PDFs are saved to `UPLOAD_DIR`, which Render wipes on every deploy and restart.
   - Deleting an account also deletes its Supabase sign-in and its stored files.
2. **Database.** Under Connect, copy the **Session pooler** connection string, fill in the database password, and set it as `DATABASE_URL`. Render can't reach the direct connection host, which is IPv6 only. The transaction pooler (port 6543) works too. Tables are created on first start. Row level security is switched on for each one, so the public anon key can't read them through Supabase's Data API. Quizzr's own connection is unaffected.
3. **Redirect URLs.** In Authentication > URL Configuration, set Site URL to your app's address (for example `https://quizzr.onrender.com`). Add `https://quizzr.onrender.com/**` and `http://localhost:3000/**` to Redirect URLs. Confirmation, password reset and Google sign-in links return to `/auth/callback` and `/reset-password`.
4. **Sign-in options.** In Authentication > Sign In / Providers:
   - Keep Email enabled, with **Confirm email** on.
   - Turn on **Allow anonymous sign-ins** for the "Continue as a guest" button.
   - For Google or GitHub, enable the provider there, then list it in `SUPABASE_OAUTH_PROVIDERS` (for example `google,github`).
5. **Email delivery.** Supabase's built-in mailer only sends to your project team's own addresses, a few per hour. Before real users sign up, add a custom SMTP provider under Authentication > Emails > SMTP Settings (Resend, Postmark, SES and others work). Until then, confirmation and reset emails won't reach anyone else.

Accounts created with Quizzr's own sign-in before the switch are kept. When someone signs up in Supabase with the same email and confirms it, their existing documents and decks are linked to the new sign-in.

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
