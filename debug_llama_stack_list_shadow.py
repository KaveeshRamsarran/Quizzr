import builtins
import llama_stack.core.conversations.conversations as conv

print("module has 'list' key?", 'list' in conv.__dict__)
print("module __dict__['list']:", conv.__dict__.get('list'))
print("builtins.list:", builtins.list, type(builtins.list))
