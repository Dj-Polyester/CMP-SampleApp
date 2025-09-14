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
class InvalidAttr(AttributeError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, var: Any, items: Sequence, and_or: str):
		super().__init__(
			f"Object of type {type(var).__name__} should have {stringify(items, and_or)}"
			f"as method or property"
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
		_type: object = Any
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
	def __init__(self, **kwargs):
		self.params = {**self.valid_params(), **self.PARAMS}
		defaults = {
			k: v.default
			for k, v in self.params.items() if v.default != Config.NON_DEFAULT
		}
		self.props = {**defaults, **kwargs}
		self._check_type()
		setattrs(self.props, self)
	def _check_type(self):
		for varname, var in self.props:
			param = self.params[varname]
			if not isinstance(var, param._type):
				raise InvalidType(varname, var, (param._type,))
	def __repr__(self):
		repr_map = {
			k: v.repr(getattr(self, k))
			for k, v in self.params.items()
		}
		return f"{self.type()}({stringify_map(repr_map)})"
	def type(self):
		return type(self).__name__
	@classmethod
	def str_func(cls, k):
		raise NotImplementedError()
	def valid_props(self):
		return {
			k: getattr(self, k) for k in self.valid_params().keys()
		}
	@classmethod
	def valid_params(cls):
		return {
			cls.str_func(k): v for k, v in cls.VALID_PARAMS.items()
		}
	@classmethod
	def valid_keys(cls):
		return list(cls.valid_params().keys())

StrConfNone = Optional[Union[str, Config]]

class TraversalUtils:
	PRECONFIGS = {}
	def setup(self, *args, **kwargs):
		raise NotImplementedError()
	def __init__(self, *args, **kwargs):
		self.setup(*args, **kwargs)
	def set_configs(self, config: StrConfNone = None, **configs: StrConfNone):
		if config != None:
			configs["config"] = config
		def set_config(config: StrConfNone):
			if isinstance(config, str):
				return self.PRECONFIGS[config]
			elif isinstance(config, Config):
				return config
			elif not exists(self, "config"):
				raise InvalidType("Config", config, (str, Config))
		setattrs_notnone(configs, self, callback_val = set_config)

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
	callback_name: Callable = lambda x: x,
	callback_val: Optional[Callable] = None,
	condition: Callable = lambda _: True,
	all_any: Union[str, bool] = "all",
	_return = True,
):
	setattrs(
		src,
		dst,
		callback_name=callback_name,
		callback_val=callback_val,
		condition=condition,
	)
	return hasattrs(dst, iterable, all_any, _return)

def setattrs_notnone(
	src: Union[Any, Collection],
	dst: Any,
	iterable: Optional[Iterable[str]] = None,
	callback_name: Callable = lambda x: x,
	callback_val: Optional[Callable] = None,
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
	callback_val: Optional[Callable] = None,
	condition: Callable = lambda _: True,
):
	"""
	Copy attributes of src to dst. If iterable of attribute names is
	provided, it is iterated upon for the attributes.
	Otherwise, the src has to inherit from 'Collection'
	"""
	if callback_val == None:
		callback_val = callback_name
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

def hasattrs(
	obj: Union[Any, Container],
	attrs: Sequence,
	all_any: Union[str, bool] = "all",
	_return = True,
):
	if all_any == "all":
		all_any = True
	elif all_any == "any":
		all_any = False
	elif not isinstance(all_any, bool):
		raise InvalidType("all_any", all_any, ("all", "any"))
	_hasattrs = all_any
	def _break_condition(attr, _bool):
		if _bool:
			_hasattrs = not _hasattrs
			return True
		return False
	def _break_condition_obj(attr):
		return _break_condition(
			attr,
			(all_any and not exists(obj, attr)) or #all
			(not all_any and exists(obj, attr)) #any
		)
	def _break_condition_container(attr):
		return _break_condition(
			attr,
			(all_any and attr not in obj) or #all
			(not all_any and attr in obj) #any
		)
	def break_condition(attr):
		if isinstance(obj, Container):
			if _break_condition_container(attr):
				return True
		elif _break_condition_obj(attr):
			return True
		return False
	for attr in attrs:
		if break_condition(attr):
			break
	if _return:
		return _hasattrs
	if not _hasattrs:
		raise InvalidAttr(obj, attrs, "and" if all_any else "or")

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
