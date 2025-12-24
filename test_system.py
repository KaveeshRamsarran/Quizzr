"""
Quick test to verify document viewing and generation are working
"""
import asyncio
import sys

async def test_system():
    print("=" * 60)
    print("QUIZZR SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Check Ollama
    print("\n1. Testing Ollama connection...")
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/version", timeout=5.0)
            version_data = resp.json()
            print(f"   ✅ Ollama running (v{version_data['version']})")
    except Exception as e:
        print(f"   ❌ Ollama connection failed: {e}")
        return False
    
    # Test 2: Check backend health
    print("\n2. Testing backend health...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:8002/health", timeout=5.0)
            health_data = resp.json()
            print(f"   ✅ Backend healthy: {health_data['app']} v{health_data['version']}")
    except Exception as e:
        print(f"   ❌ Backend connection failed: {e}")
        return False
    
    # Test 3: Quick LLM generation test
    print("\n3. Testing local LLM generation...")
    try:
        # Change to backend directory to import app modules
        sys.path.insert(0, 'C:/Users/User/Downloads/Quizzr/backend')
        from app.services.llm import get_llm_client
        
        client = get_llm_client()
        result = await client.generate_json(
            "Generate a simple flashcard about Python. Return JSON: {\"front\": \"question\", \"back\": \"answer\"}",
            temperature=0.7,
            max_tokens=200
        )
        
        if result and 'front' in result and 'back' in result:
            print(f"   ✅ LLM generation working")
            print(f"      Front: {result['front']}")
            print(f"      Back: {result['back'][:100]}...")
        else:
            print(f"   ❌ LLM returned invalid response: {result}")
            return False
    except Exception as e:
        print(f"   ❌ LLM generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Check database for documents
    print("\n4. Checking database for documents...")
    try:
        import sqlite3
        conn = sqlite3.connect('C:/Users/User/Downloads/Quizzr/backend/quizzr.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM documents')
        doc_count = cursor.fetchone()[0]
        print(f"   ✅ Found {doc_count} documents in database")
        
        if doc_count > 0:
            cursor.execute('SELECT id, original_filename, file_path FROM documents ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            print(f"      Latest: ID={row[0]}, File={row[1]}, Path={row[2]}")
        
        conn.close()
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nQuizzr is ready to use:")
    print("  • Frontend: http://localhost:3000")
    print("  • Backend:  http://127.0.0.1:8002")
    print("  • LLM:      Local Ollama (llama3.2:3b)")
    print("\nYou can now:")
    print("  1. Upload PDF documents")
    print("  2. View uploaded documents")
    print("  3. Generate flashcards/quizzes using local AI")
    print()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_system())
    sys.exit(0 if success else 1)
