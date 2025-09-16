from typing import Callable, Iterable, Union, Optional, Any, Mapping
from types import FunctionType, MethodType
from utils import exists, product_dict

def ret_callable(
	attr: Union[FunctionType, MethodType],
	prefix: Optional[Callable] = None,
	postfix: Optional[Callable] = None,
	prefix_kwargs: Mapping[str,Any] = {},
	postfix_kwargs: Mapping[str,Any] = {},
):
	if isinstance(attr, (FunctionType, MethodType)):
		_oldcall = attr
	else:
		raise TypeError(f"attr has wrong type {type(attr)}")
	def _newcall(*args, **kwargs):
		if prefix != None:
			prefix(**prefix_kwargs)
		_oldcall(*args, **kwargs)
		if postfix != None:
			postfix(**postfix_kwargs)
	return _newcall
class Test:
	"""
	A singleton class for unit tests.
	A single call runs every public method name of which does not start with `_`
	"""
	_instance = None
	def __new__(cls, *args, **kwargs):
		if not cls._instance:  # If no instance exists
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		self._setup()

	def _modifyattr(self, attr_name: str):
		attr = getattr(self, attr_name)
		setattr(
			self,
			attr_name,
			ret_callable(
				attr,
				self._entry,
				prefix_kwargs = {"attr_name": attr_name},
			)
		)

	def _setup(self):
		if not exists(self, "_initialized"):
			self._initialized = True
			self._forallattrs(self._modifyattr)

	def _entry(self, attr_name: str):
		print(f"Running test {attr_name}")

	def _forallattrs(self, callback: Callable):
		for attr_name in dir(self):
			if not attr_name.startswith("_"):
				callback(attr_name)

	def _compare_classes(
		self,
		cls_types: Iterable[type],
		params: Mapping[str, Any],
		_callback_inner: Callable,
		_callback_outer: Callable,
	):
		buffer_txts = []
		for param in product_dict(params):
			print(f"\nParameters: {param}")
			for cls_type in cls_types:
				res = _callback_inner(cls_type, param)
				buffer_txts.append(res)
			_callback_outer(buffer_txts)


	def __call__(self):
		self._forallattrs(
			lambda attr_name: getattr(self, attr_name)()
		)

if __name__ == "__main__":
	class TestDummy(Test):
		def a(self):
			print(f"in a")
		@classmethod
		def b(cls):
			print(f"in b")
		@staticmethod
		def c():
			print(f"in c")
		def _a(self):
			print(f"in _a")
		@classmethod
		def _b(cls):
			print(f"in _b")
		@staticmethod
		def _c():
			print(f"in _c")
	t1 = TestDummy()
	t1()
	t2 = TestDummy()
	assert t1 == t2
	t2()
