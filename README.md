# 🎓 Quizzr

An AI-powered flashcard and quiz generation application that transforms PDF documents into interactive study materials using advanced natural language processing.

![Quizzr](https://img.shields.io/badge/Status-Production%20Ready-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 📚 Smart Document Processing
- **PDF Upload & Processing**: Support for text-based and scanned PDFs with OCR fallback
- **Intelligent Chunking**: Auto-detects document type (notes, slides, textbook) for optimal processing
- **Full-Text Search**: Find content across all your uploaded documents

### 🃏 AI-Powered Flashcard Generation
- **Automatic Card Creation**: Generates question-answer pairs from document content
- **Anti-Hallucination**: Two-stage prompting ensures cards are grounded in source material
- **Multiple Card Types**: Basic, cloze deletion, and image-based cards
- **Difficulty Calibration**: Cards are tagged with difficulty levels (easy, medium, hard)

### 📝 Quiz Generation
- **Multiple Question Types**: Multiple choice, true/false, fill-in-the-blank, short answer
- **Customizable Quizzes**: Set time limits, passing scores, and question counts
- **Performance Tracking**: Track attempts, scores, and progress over time

### 🧠 Spaced Repetition System
- **SM-2 Algorithm**: Scientifically-proven algorithm optimizes review timing
- **Personalized Scheduling**: Cards are scheduled based on individual performance
- **Streak Tracking**: Maintain study streaks to build consistent habits

### 📊 Analytics & Insights
- **Study Statistics**: Track cards studied, time spent, and mastery levels
- **Topic Mastery**: Visualize strength across different topics
- **Performance Trends**: Charts showing progress over time

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (React)                          │
│    React 18 │ TypeScript │ TailwindCSS │ React Query │ Zustand │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                      │
│         JWT Auth │ Rate Limiting │ CORS │ Validation           │
└────────┬────────────────────┬────────────────────┬──────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ PostgreSQL  │    │   Redis/Celery   │    │    OpenAI API   │
│  Database   │    │   Task Queue     │    │  GPT-4 Turbo    │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/quizzr.git
cd quizzr

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and set your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-api-key-here
SECRET_KEY=your-secure-secret-key-min-32-chars
```

### 3. Start with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API (Redoc)**: http://localhost:8000/redoc

## 📁 Project Structure

```
quizzr/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── services/        # Business logic layer
│   │   ├── routers/         # API route handlers
│   │   ├── tasks/           # Celery background tasks
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection
│   │   ├── celery_app.py    # Celery configuration
│   │   └── main.py          # FastAPI application
│   ├── tests/               # Backend tests
│   ├── uploads/             # Uploaded files (gitignored)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   ├── pages/           # Page components
│   │   ├── stores/          # Zustand state stores
│   │   ├── lib/             # API client & utilities
│   │   ├── types/           # TypeScript type definitions
│   │   └── App.tsx          # Main application component
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔌 API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login and get tokens |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/auth/guest` | POST | Create guest account |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/documents` | GET | List user's documents |
| `/api/v1/documents` | POST | Upload new document |
| `/api/v1/documents/{id}` | GET | Get document details |
| `/api/v1/documents/{id}` | DELETE | Delete document |

### Decks & Cards

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/decks` | GET | List user's decks |
| `/api/v1/decks` | POST | Create new deck |
| `/api/v1/decks/{id}` | GET | Get deck with cards |
| `/api/v1/decks/{id}/cards` | POST | Add card to deck |
| `/api/v1/decks/{id}/due` | GET | Get cards due for review |
| `/api/v1/decks/{id}/study` | POST | Submit study session |

### Quizzes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/quizzes` | GET | List user's quizzes |
| `/api/v1/quizzes` | POST | Create new quiz |
| `/api/v1/quizzes/{id}/attempts` | POST | Start quiz attempt |
| `/api/v1/quizzes/{id}/attempts/{aid}/answers` | POST | Submit answer |
| `/api/v1/quizzes/{id}/attempts/{aid}/finish` | POST | Finish attempt |

### Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/generation/deck` | POST | Generate deck from document |
| `/api/v1/generation/quiz` | POST | Generate quiz from document |
| `/api/v1/generation/jobs` | GET | Get generation job status |

### Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics` | GET | Get user analytics |
| `/api/v1/analytics/streak` | GET | Get streak information |

## 🧪 Running Tests

### Backend Tests

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

### Frontend Tests

```bash
cd frontend
npm test

# Run with coverage
npm run test:coverage
```

## 🔧 Development

### Running Locally (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (required)
# Then run the application
uvicorn app.main:app --reload

# In another terminal, start Celery worker
celery -A app.celery_app worker --loglevel=info

# In another terminal, start Celery beat
celery -A app.celery_app beat --loglevel=info
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | JWT signing key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | Model to use | `gpt-4-turbo-preview` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |

## 🎯 Spaced Repetition (SM-2) Algorithm

Quizzr implements the SuperMemo 2 algorithm for optimal card scheduling:

```
EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))

Where:
- EF = Ease Factor (starts at 2.5)
- q = Quality of response (0-5)
  - 0-1: Complete failure ("Again")
  - 2-3: Difficult recall ("Hard")
  - 4: Correct with effort ("Good")
  - 5: Perfect recall ("Easy")
```

**Interval calculation:**
- First review: 1 day
- Second review: 6 days
- Subsequent: `interval * EF`

## 🔒 Security Features

- **JWT Authentication** with access and refresh tokens
- **Password Hashing** using bcrypt
- **Rate Limiting** on sensitive endpoints
- **CORS Protection** for API requests
- **Input Validation** with Pydantic schemas
- **SQL Injection Prevention** via SQLAlchemy ORM

## 📈 Scaling Considerations

- **Horizontal Scaling**: Stateless API design allows multiple backend instances
- **Task Queue**: Celery with Redis handles long-running AI generation tasks
- **Database**: PostgreSQL with async support for high concurrency
- **Caching**: Redis caching for frequently accessed data
- **CDN**: Static frontend can be served via CDN

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - UI library
- [OpenAI](https://openai.com/) - GPT-4 API
- [SuperMemo](https://www.supermemo.com/) - SM-2 algorithm
- [Tailwind CSS](https://tailwindcss.com/) - Styling framework

---

Built with ❤️ for students and lifelong learners