from typing import Any

def exists(obj: Any, attr: str) -> bool:
	return hasattr(obj, attr) and getattr(obj, attr) != None
def tabbed_print(depth: int, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
