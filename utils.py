from typing import (
	Union,
	Any,
	Iterable,
	Optional,
	Collection,
	Sequence,
	Mapping,
	MutableMapping,
	Callable,
	Container,
)
import itertools
from dataclasses import dataclass, field

class InvalidType(TypeError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, varname: str, var, items: Sequence):
		super().__init__(
			f"The {varname} has to be of type {stringify(items, 'or')} "
			f"but has type {type(var)}"
		)
class InvalidValue(ValueError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, varname: str, var, items: Sequence):
		super().__init__(
			f"The {varname} has to be {stringify(items, 'or')} "
			f"but is {var}"
		)


@dataclass
class State:
	success: Optional[bool]
	def completed(self):
		return not isneg(self.success)
	def failed(self):
		return isneg(self.success)
class Config:
	NON_DEFAULT = None
	@dataclass
	class Param:
		default: Any = None
		repr: Callable = lambda x: x
		def __post_init__(self):
			if self.default is None:
				self.default = Config.NON_DEFAULT
	PROPERTIES = (
		"str_func",
	)
	PARAMS: Mapping[str, Param] = {}
	VALID_PARAMS: Mapping[str, Param] = {}
	def str_func(self, k):
		raise NotImplementedError()
	def __init__(self, **kwargs):
		valid_params: Mapping[str, Config.Param] = {
			self.str_func(k): v for k, v in self.VALID_PARAMS.items()
		}
		self.params = {**valid_params, **self.PARAMS}
		defaults = {
			k: v.default
			for k, v in self.params.items() if v.default != Config.NON_DEFAULT
		}
		props = {**defaults, **kwargs}
		setattrs(props, self)
	def __repr__(self):
		repr_map = {
			k: v.repr(getattr(self, k))
			for k, v in self.params.items()
		}
		return f"{self.type()}({stringify_map(repr_map)})"
	def type(self):
		return type(self).__name__

def product_dict(
	valid_mapping: Mapping,
	condition: Callable = lambda **_: True,

):
	"""
	Given a `valid_mapping` of key value pairs as (name, iterable_of_valid_values),
	generates a mapping that satisfies `condition` for each iteration as
	(name, possible_value) using cartesian product.

	Usage:
```
for combination in product_dict(valid_mapping, condition):
	# Do sth with the combination
	...
```
	"""
	keys = valid_mapping.keys()
	iter_of_valid_vals = valid_mapping.values()
	for val_comb in itertools.product(*iter_of_valid_vals):
		comb = dict(zip(keys, val_comb))
		if condition(**comb):
			yield comb

def setattrs_check(
	src: Union[Any, Collection],
	dst: Any,
	iterable: Sequence,
	callback: Callable = lambda x: x,
	condition: Callable = lambda _: True,
):
	setattrs(
		src,
		dst,
		callback=callback,
		condition=condition,
	)
	if not hasattrs_all(dst, iterable):
		raise AttributeError(
			f"Object should implement or provide {stringify(iterable)} as parameters"
		)

def setattrs_notnone(
	src: Union[Any, Collection],
	dst: Any,
	iterable: Optional[Iterable[str]] = None,
	callback_name: Callable = lambda x: x,
	callback_val: Callable = lambda x: x,
):
	setattrs(
		src,
		dst,
		iterable,
		callback_name,
		callback_val,
		lambda x: x != None,
	)

def setattrs(
	src: Union[Any, Collection],
	dst: Any,
	iterable: Optional[Iterable[str]] = None,
	callback_name: Callable = lambda x: x,
	callback_val: Callable = lambda x: x,
	condition: Callable = lambda _: True,
):
	"""
	Copy attributes of src to dst. If iterable of attribute names is
	provided, it is iterated upon for the attributes.
	Otherwise, the src has to inherit from 'Collection'
	"""
	def getfunc(obj: Any):
		return obj.__getitem__ if isinstance(obj, MutableMapping) else obj.__getattribute__
	def setfunc(obj: Any):
		return obj.__setitem__ if isinstance(obj, MutableMapping) else obj.__setattr__
	if iterable == None:
		if isinstance(src, Collection):
			iterable = src
		else:
			raise TypeError(f"src parameter of type {type(src)} should be 'Collection'")
	src_getfunc = getfunc(src)
	dst_setfunc = setfunc(dst)
	for name in iterable:
		src_val = src_getfunc(callback_name(name))
		if condition(src_val):
			dst_setfunc(name, callback_val(src_val))

def hasattrs_all(obj: Union[Any, Container], attrs: Iterable):
	for attr in attrs:
		if isinstance(obj, Container):
			if attr not in obj:
				return False
		elif not exists(obj, attr):
			return False
	return True

def hasattrs_any(obj: Union[Any, Container], attrs: Iterable):
	for attr in attrs:
		if isinstance(obj, Container):
			if attr in obj:
				return True
		elif exists(obj, attr):
			return True
	return False

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

def stringify_map(map: Mapping):
	return stringify([f"{k}={v}" for k, v in map.items()])
def stringify(items: Sequence, and_or: str = ", "):
	return ", ".join(items[:-1]) + f" {and_or} " + items[-1]
def getattr_none(obj: Any, name: str):
	return getattr(obj, name) if hasattrs_all(obj, name) else None
def isneg(res):
	return isinstance(res, bool) and not res
def exists(obj: Any, attr: str) -> bool:
	return hasattr(obj, attr) and getattr(obj, attr) != None
def tabbed_print(depth: int, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
