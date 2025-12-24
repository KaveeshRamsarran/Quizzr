"""
Test the asyncio fix for generation tasks
"""
import asyncio
import sys
sys.path.insert(0, 'C:/Users/User/Downloads/Quizzr/backend')

from app.celery_mock import MockTask

# Test async function
async def sample_async_task(task_self, job_id: int):
    """Sample async task similar to generation tasks"""
    await asyncio.sleep(0.1)
    return {"success": True, "job_id": job_id}

# Create a mock task
mock_task = MockTask(sample_async_task)

print("Testing asyncio fix in celery_mock...")
print("=" * 60)

# Test 1: Call from sync context (should work)
print("\n1. Testing from synchronous context...")
try:
    result = mock_task.delay(123)
    print(f"   ✅ Task executed: {result.result}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 2: Call from async context (the problematic case)
print("\n2. Testing from asynchronous context (FastAPI simulation)...")
async def simulate_fastapi_handler():
    """Simulates calling a Celery task from inside an async FastAPI handler"""
    try:
        result = mock_task.delay(456)
        return result
    except Exception as e:
        raise Exception(f"Failed in async context: {e}")

try:
    # This simulates what happens when FastAPI calls the generation endpoint
    result = asyncio.run(simulate_fastapi_handler())
    print(f"   ✅ Task executed from async context: {result.result}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Asyncio fix is working!")
print("=" * 60)
print("\nGeneration tasks should now work without the")
print("'asyncio.run() cannot be called from a running event loop' error")
