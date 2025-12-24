import os
import traceback

CONFIG = os.environ.get(
    "LLAMA_STACK_CONFIG",
    r"C:\Users\User\Downloads\Quizzr\llama-stack.quizzr-local.yaml",
)
os.environ["LLAMA_STACK_CONFIG"] = CONFIG

try:
    from llama_stack.core.server.server import create_app

    create_app()
    print("create_app() OK")
except Exception as e:
    print("create_app() FAILED:", repr(e))
    traceback.print_exc()
    raise
