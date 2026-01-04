"""Test deck generation task."""
from sqlalchemy import create_engine, text
from app.config import settings
from app.tasks.generation_tasks import generate_deck_task
from app.schemas.generation import DeckGenerationRequest

url = settings.database_url
if '+aiosqlite' in url:
    url = url.replace('+aiosqlite', '')

engine = create_engine(url)

# First create a generation job
with engine.connect() as conn:
    # Insert a new job for deck generation
    conn.execute(text("""
        INSERT INTO processing_jobs (user_id, job_type, status, parameters, created_at, progress)
        VALUES (2, 'deck_generation', 'PENDING', '{}', datetime('now'), 0)
    """))
    conn.commit()
    
    # Get the job ID
    result = conn.execute(text('SELECT MAX(id) FROM processing_jobs'))
    job_id = result.fetchone()[0]
    print(f'Created job ID: {job_id}')

# Create request data
request_data = {
    "document_id": 1,
    "card_count": 5,
    "difficulty": "medium",
    "verify": False,  # Skip verification for faster test
    "include_basic": True,
    "include_definitions": True,
    "include_concepts": True,
    "include_processes": False,
    "include_formulas": False,
    "include_cloze": False,
    "include_eli5": False,
    "include_examples": False,
    "include_mnemonics": False,
    "max_cards": 10,
}

print('Running deck generation task...')
print('This will call Ollama to generate content - may take a minute...')
try:
    result = generate_deck_task.delay(job_id, request_data)
    print(f'Task result: {result.state} - {result.result}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
