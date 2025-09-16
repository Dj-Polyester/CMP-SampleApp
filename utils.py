import itertools
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
	ClassVar,
	KeysView,
)
from dataclasses import dataclass, field

class InvalidType(TypeError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, varname: str, var, items: Union[Any, Sequence]):
		super().__init__(
			f"The {varname} has to be of type {stringify(items, 'or')} "
			f"but has type {type(var)}"
		)
class InvalidVal(ValueError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, varname: str, var, items: Union[Any, Sequence]):
		super().__init__(
			f"The {varname} has to be {stringify(items, 'or')} "
			f"but is {var}"
		)
class InvalidAttr(AttributeError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, var: Any, items: Union[Any, Sequence], and_or: str = ","):
		super().__init__(
			f"Object of type {type(var).__name__} should have {stringify(items, and_or)} "
			f"as method or property"
		)
@dataclass
class State:
	success: Optional[bool]
	def completed(self):
		return not isneg(self.success)
	def failed(self):
		return isneg(self.success)

@dataclass
class Param:
	NON_DEFAULT: ClassVar[Any] = ...
	DEFAULT: ClassVar[Any] = None
	_type: object = object
	default: Any = DEFAULT
	repr: Callable = field(default=lambda x: x, repr=False)
	def __postinit__(self):
		if self._type == Callable and self.default == Param.DEFAULT:
			self.repr = lambda x: x.__name__

class Config:
	PROPERTIES = (
		"str_func",
	)
	PARAMS: Mapping[str, Param] = {}
	VALID_PARAMS: Mapping[str, Param] = {}
	SUBSTR: str = ""
	def __init__(self, **kwargs):
		self._params = self.params()
		self._defaults = {
			k: v.default
			for k, v in self._params.items() if v.default != Param.DEFAULT
		}
		self._props = {**self._defaults, **kwargs}
		self._check_type()
		Attrs().set_check(
			self._props,
			self,
			_return = False,
		)
	def is_equal(self, other: 'Config'):
		return self._props == other._props
	def _check_type(self):
		for varname, var in self._props.items():
			param = self._params[varname]
			if not isinstance(var, param._type):
				raise InvalidType(varname, var, param._type)
	def __repr__(self):
		repr_map = {
			k: v.repr(getattr(self, k))
			for k, v in self._params.items()
		}
		return f"{self.type()}({stringify_map(repr_map)})"
	def type(self):
		return type(self).__name__
	@classmethod
	def str_func(cls, k, substr) -> str:
		raise NotImplementedError()
	@classmethod
	def _str_func(
		cls,
		s1: Optional[str] = Param.DEFAULT,
		s2: Optional[str] = Param.DEFAULT,
		reverse: bool = False,
		delim: str = "_",
		char: str = "",
	) -> str:
		if s1 == Param.DEFAULT: s1 = cls.SUBSTR
		if s2 == Param.DEFAULT: s2 = cls.SUBSTR
		_str = f"{s1}{delim}{s2}" if not reverse else f"{s2}{delim}{s1}"
		return s2 if s1==char else _str
	def props(self, *args, **kwargs):
		return {
			k: getattr(self, k) for k in self.params(*args, **kwargs).keys()
		}
	def defaults(self, *args, **kwargs):
		return {
			k: v.default
			for k, v in self.params(*args, **kwargs).items()
			if v.default != Param.DEFAULT
		}
	@classmethod
	def params(
		cls,
		_type: str = "all",
	) -> Mapping[str, Param]:
		_map = Param.DEFAULT
		_callback = lambda k: k
		if _type == "valid":
			_map = cls.VALID_PARAMS
			_callback = lambda k: cls.str_func(k, cls.SUBSTR)
		elif _type == "other":
			_map = cls.PARAMS
		elif _type == "all":
			_map = {**cls.PARAMS, **cls.params("valid")}
		else:
			raise InvalidVal("_type", _type, ("valid", "other", "all"))
		return {
			_callback(k): v for k, v in _map.items()
		}
	@classmethod
	def keys(cls, *args, **kwargs) -> KeysView[str]:
		return cls.params(*args, **kwargs).keys()

StrConfNone = Optional[Union[str, Config]]

class TraversalUtils:
	PRECONFIGS = {}
	def __init__(self, *args, **kwargs):
		self.setup(*args, **kwargs)
	def setup(self, *args, **kwargs):
		raise NotImplementedError()
	def set_configs(self, config: StrConfNone = Param.DEFAULT, **configs: StrConfNone):
		if config != Param.DEFAULT:
			configs["config"] = config
		def set_config(config: StrConfNone):
			if isinstance(config, str):
				return self.PRECONFIGS[config]
			elif isinstance(config, Config):
				return config
			elif not exists(self, "config"):
				raise InvalidType("Config", config, (str, Config))
		Attrs(callback_val = set_config).set(configs, self)
		pass
	def props(self, config: Config, *args, **kwargs):
		return {
			k: getattr(self, k) for k in config.params(*args, **kwargs).keys()
		}
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

class Attrs:
	def __init__(
		self, *args, **kwargs,
	):
		self._with(*args, **kwargs)
	def _with(
		self,
		iterable: Optional[Iterable[str]] = Param.DEFAULT,
		callback_name: Callable = lambda x: x,
		callback_val: Callable = lambda x: x,
		condition_name: Callable = lambda _: True,
		condition_val: Callable = lambda _: True,
	):
		self.iterable = iterable
		self.callback_name = callback_name
		self.callback_val = callback_val
		self.condition_name = condition_name
		self.condition_val = condition_val
		return self
	def _helper_iter(
		self,
		src: Union[Any, Collection],
	):
		if self.iterable == Param.DEFAULT:
			if isinstance(src, Collection):
				self.iterable = src
			else:
				raise TypeError(f"src parameter of type {type(src)} should be 'Collection'")
	@staticmethod
	def getitem(obj: Any, name: str):
		return (
			obj.__getitem__(name)
			if isinstance(obj, Mapping)
			else obj.__getattribute__(name)
		)
	@staticmethod
	def setitem(obj: Any, name: str, value: Any):
		(
			obj.__setitem__(name, value)
			if isinstance(obj, MutableMapping)
			else obj.__setattr__(name, value)
		)

	def _helper_getfunc(
		self,
		src: Union[Any, Collection],
	):
		self._helper_iter(src)
		def getfunc(obj: Any):
			def _getfunc(x):
				if self.condition_name(x):
					return Attrs.getitem(obj, x)
				else:
					return Param.DEFAULT
			return _getfunc
		self.src_getfunc = getfunc(src)
	def get(
		self,
		src: Any,
	):
		"""
		Returns `src` if it is a `Mapping` attributes otherwise.
		"""
		self._helper_getfunc(src)
		def _attr_gen():
			for name in self.iterable:
				src_val = self.src_getfunc(self.callback_name(name))
				if self.condition_val(src_val):
					yield name, self.callback_val(src_val)
		return {k:v for k, v in _attr_gen()}
	def set(
		self,
		src: Any,
		dst: Any,
	):
		"""
		Copies attributes or values of `src` to `dst`
		depending on whether they are `Mapping` or not.
		"""
		self._helper_getfunc(src)
		def setfunc(obj: Any):
			return lambda name, val: Attrs.setitem(obj, name, val)
		self.dst_setfunc = setfunc(dst)
		for name in self.iterable:
			src_val = self.src_getfunc(self.callback_name(name))
			if self.condition_val(src_val):
				self.dst_setfunc(name, self.callback_val(src_val))
	def has(
		self,
		obj: Union[Any, Container],
		attrs: Optional[Iterable] = Param.DEFAULT,
		all_any: Union[str, bool] = "all",
		_return = True,
	):
		"""
		Checks if `obj` has `attrs`. if `attrs` is `None`, `iterable` is provided.
		"""
		if attrs == Param.DEFAULT:
			attrs = self.iterable
		if all_any == "all":
			all_any = True
		elif all_any == "any":
			all_any = False
		elif not isinstance(all_any, bool):
			raise InvalidType("all_any", all_any, ("all", "any"))
		_hasattrs = all_any
		def _break_condition(_bool):
			nonlocal _hasattrs
			if _bool:
				_hasattrs = not _hasattrs
				return True
			return False
		def _break_condition_obj(attr):
			return _break_condition(
				(all_any and not exists(obj, attr)) or #all
				(not all_any and exists(obj, attr)) #any
			)
		def _break_condition_container(attr):
			return _break_condition(
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
	def set_check(
		self,
		src: Union[Any, Collection],
		dst: Any,
		*has_args, **has_kwargs,
	):
		"""
		Checks to see if the elements copied successfully.
		"""
		self.set(src, dst)
		self.has(dst, *has_args, **has_kwargs)


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
def stringify(items: Union[Any, Sequence], and_or: str = ","):
	if not isinstance(items, Sequence) or isinstance(items, str):
		items = (items,)
	and_or_str = ", " if and_or == "," else f" {and_or} "
	return ", ".join(items[:-1]) + f"{and_or_str}{items[-1]}"
def isneg(res):
	return isinstance(res, bool) and not res
def exists(obj: Any, name: str) -> bool:
	"""
	Check if obj has attr with `name`.
	Evaluates to the same operation as below expression
	except it uses object.__getattribute__ to avoid recursion.
	`return hasattr(obj, name) and getattr(obj, name) != None`
	"""
	attr = None
	try:
		attr = object.__getattribute__(obj, name)
	except AttributeError:
		pass
	return attr != None
def tabbed_print(depth: int, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
def xnor(a:bool,b:bool):
	return (a and b) or (not a and not b)
