"""
Test script to verify Ollama-based generation is working
"""
import asyncio
import httpx

async def test_ollama_chat():
    """Test direct Ollama API call"""
    print("Testing Ollama chat endpoint...")
    
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2:3b",
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert educational content creator. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": """Generate 2 flashcards about Python programming. Return JSON in this format:
{
  "flashcards": [
    {
      "front": "What is a Python list?",
      "back": "A Python list is an ordered, mutable collection of items."
    }
  ]
}"""
            }
        ],
        "options": {
            "temperature": 0.7,
            "num_predict": 500
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "")
            print("\n✅ Ollama Response:")
            print(content)
            
            # Try to parse as JSON
            import json
            try:
                parsed = json.loads(content)
                print("\n✅ Successfully parsed as JSON!")
                print(f"Generated {len(parsed.get('flashcards', []))} flashcards")
                for i, card in enumerate(parsed.get('flashcards', []), 1):
                    print(f"\nCard {i}:")
                    print(f"  Front: {card.get('front', 'N/A')}")
                    print(f"  Back: {card.get('back', 'N/A')}")
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON: {e}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")

async def test_backend_health():
    """Test Quizzr backend health"""
    print("\n" + "="*60)
    print("Testing Quizzr backend health...")
    
    url = "http://127.0.0.1:8002/health"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Backend is healthy: {data}")
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")

async def main():
    print("="*60)
    print("QUIZZR + OLLAMA GENERATION TEST")
    print("="*60)
    
    await test_ollama_chat()
    await test_backend_health()
    
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Open http://localhost:3000 in your browser")
    print("2. Create an account or login")
    print("3. Upload a PDF document")
    print("4. Generate flashcards or quiz using local Llama3.2:3b model")
    print("\nConfiguration:")
    print("- LLM_PROVIDER=ollama")
    print("- LLM_MODEL=llama3.2:3b")
    print("- OLLAMA_BASE_URL=http://localhost:11434")

if __name__ == "__main__":
    asyncio.run(main())
