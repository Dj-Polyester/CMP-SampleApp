from typing import Any, Iterable, Optional, Collection, Sequence

STATUS = [
	"✓",
	"✗",
	"⚠",
]

def status_msg(code: int):
	try:
		return STATUS[code]
	except IndexError:
		raise ValueError(f"Invalid status {code}")

def setattrs(src: Collection, dst: Any, iterable: Optional[Iterable] = None):
	def getfunc(obj: Any):
		return obj.__getitem__ if isinstance(obj, dict) else obj.__getattribute__
	def setfunc(obj: Any):
		return obj.__setitem__ if isinstance(obj, dict) else obj.__setattr__
	if iterable == None:
		iterable = src
	src_getfunc = getfunc(src)
	dst_setfunc = setfunc(dst)
	for name in iterable:
		dst_setfunc(name, src_getfunc(name))
def hasattrs(obj: Any, attrs: Iterable):
	for attr in attrs:
		if not exists(obj, attr):
			return False
	return True

def stringify(items: Sequence, and_or = "and"):
	return ", ".join(items[:-1]) + f" {and_or} " + items[-1]

def getattr_none(obj: Any, name: str):
	return getattr(obj, name) if hasattrs(obj, name) else None

def _not_implemented(*args, **kwargs):
    raise NotImplementedError()
def exists(obj: Any, attr: str) -> bool:
	return hasattr(obj, attr) and getattr(obj, attr) != None
def tabbed_print(depth: int, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
