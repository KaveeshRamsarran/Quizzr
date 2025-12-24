"""
Celery Mock for Local Development
Provides mock implementations when Celery is not available
"""

import asyncio
import inspect
import concurrent.futures
from functools import wraps


class MockAsyncResult:
    """Mock Celery AsyncResult"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.state = "PENDING"
        self.result = None
    
    def ready(self):
        return True
    
    def successful(self):
        return True
    
    def get(self, timeout=None):
        return self.result


class MockTask:
    """Mock Celery Task"""
    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        wraps(func)(self)
    
    def delay(self, *args, **kwargs):
        """Execute synchronously and return mock result"""
        result = MockAsyncResult(f"mock-{self.name}")
        try:
            call_args = list(args)

            # Support Celery bound-task signatures: def task(self, ...)
            # Real Celery injects `self` automatically; our mock must do it.
            try:
                sig = inspect.signature(self.func)
                params = list(sig.parameters.values())
                if params and params[0].name in {"self", "task"}:
                    # If caller didn't provide the bound self explicitly, inject it.
                    if len(call_args) == (len(params) - 1):
                        dummy = type("MockBoundTask", (), {})()
                        dummy.request = type("MockRequest", (), {"id": f"mock-{self.name}"})()
                        call_args = [dummy] + call_args
            except Exception:
                # If signature inspection fails, just proceed
                pass

            def _invoke():
                if asyncio.iscoroutinefunction(self.func):
                    return asyncio.run(self.func(*call_args, **kwargs))
                return self.func(*call_args, **kwargs)

            # Important: Even if the task function itself is sync, it may call
            # asyncio.run() internally (our generation tasks do). When called
            # from inside FastAPI's running event loop, run the whole task in a
            # separate thread to avoid nested event loop errors.
            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_invoke)
                    result.result = future.result()
            except RuntimeError:
                # No running loop in this thread.
                result.result = _invoke()

            result.state = "SUCCESS"
        except Exception as e:
            result.state = "FAILURE"
            result.result = str(e)
        return result
    
    def apply_async(self, args=None, kwargs=None, **options):
        """Execute synchronously and return mock result"""
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def shared_task(*args, **kwargs):
    """Mock shared_task decorator"""
    def decorator(func):
        return MockTask(func)
    
    # Handle both @shared_task and @shared_task() syntax
    if len(args) == 1 and callable(args[0]):
        return MockTask(args[0])
    return decorator


class MockCeleryControl:
    """Mock Celery control interface"""
    def revoke(self, task_id, terminate=False, signal=None):
        pass
    
    def inspect(self):
        return MockInspect()


class MockInspect:
    """Mock Celery inspect interface"""
    def active(self):
        return {}
    
    def scheduled(self):
        return {}
    
    def reserved(self):
        return {}


class MockCelery:
    """Mock Celery app for local development"""
    def __init__(self, name="mock", **kwargs):
        self.name = name
        self.control = MockCeleryControl()
        self.conf = type('Config', (), {
            'update': lambda self, **kw: None,
            'beat_schedule': {}
        })()
    
    def task(self, *args, **kwargs):
        """Mock task decorator"""
        return shared_task(*args, **kwargs)
    
    def send_task(self, name, args=None, kwargs=None, **options):
        result = MockAsyncResult(f"mock-{name}")
        result.state = "PENDING"
        return result


# Create a mock celery instance
celery = MockCelery("quizzr")
celery_app = celery


# Provide Celery-like interface
class Celery:
    """Mock Celery class"""
    def __new__(cls, *args, **kwargs):
        return MockCelery(*args, **kwargs)
