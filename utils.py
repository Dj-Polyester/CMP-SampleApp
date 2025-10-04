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
import sys

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

class InvalidType(TypeError):
	"""Raised when a variable has an invalid type"""
	def __init__(self, varname: str, var, items: Union[Any, Sequence]):
		super().__init__(
			f"The {varname} has to be of type {stringify(items, 'or')} "
			f"but has type {type(var)}"
		)
class InvalidVal(ValueError):
	"""Raised when a variable has an invalid value"""
	def __init__(self, varname: str, var, items: Union[Any, Sequence]):
		super().__init__(
			f"The {varname} has to be {stringify(items, 'or')} "
			f"but is {var}"
		)
class InvalidAttr(AttributeError):
	"""Raised when a variable has an invalid attribute"""
	def __init__(self, var: Any, items: Union[Any, Sequence], and_or: str = ","):
		super().__init__(
			f"Object of type {type(var).__name__} should have {stringify(items, and_or)} "
			f"as method or property"
		)

class Singleton:
	_instance = None
	def __new__(cls, *args, **kwargs):
		if not cls._instance:  # If no instance exists
			cls._instance = super().__new__(cls)
		return cls._instance
@dataclass
class Status:
	txt: str
	logo: str
	e: type = Param.DEFAULT

@dataclass
class Result:
	STATUS: ClassVar = [
		Status("done", "✓"),
		Status("failed", "✗"),
		Status("interrupted", "⚠", KeyboardInterrupt),
	]
	code: int = -1
	return_value: Optional[Any] = Param.DEFAULT
	def set_code(self, e: Optional[Union[BaseException, bool, int]] = Param.DEFAULT):
		if isinstance(e, bool):
			self.code = int(not e)
		elif isinstance(e, int):
			lenst = len(self.STATUS)
			if e >= lenst:
				raise InvalidVal("Result code", e, tuple(range(lenst)))
			self.code = e
		elif isinstance(e, KeyboardInterrupt):
			self.code = 2
		elif isinstance(e, BaseException):
			self.code = 1
		elif e != None:
			self.code = 0
	def completed(self):
		return self.code == 0
	def failed(self):
		return self.code == 1
	def interrupted(self):
		return self.code == 2
	def exists(self):
		return self.code != -1
	def none(self):
		return self.code == -1
	def status_msg(self, code: Optional[int] = Param.DEFAULT):
		if code == Param.DEFAULT:
			code = self.code
		try:
			status = Result.STATUS[code]
		except IndexError:
			raise ValueError(f"Invalid status {code}")
		return f"{status.txt} {status.logo}"

@dataclass
class State:
	result: Optional[Result] = Param.DEFAULT

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
		def get_config(config: StrConfNone):
			if isinstance(config, str):
				return self.PRECONFIGS[config]
			elif isinstance(config, Config):
				return config
			elif not Attrs.has(self, "config"):
				raise InvalidType("Config", config, (str, Config))
		Attrs(callback_val = get_config).set(configs, self)
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
	def _with_notnone(
		self,
		callback_name: Callable = lambda x: x,
		callback_val: Callable = lambda x: x,
	):
		return self._with(
			self.iterable,
			callback_name,
			callback_val,
			condition_name = lambda name: Attrs.has(self, name),
			condition_val = lambda val: val != Param.DEFAULT,
		)
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
	def _getitem(obj: Any, name: str):
		return (
			obj.__getitem__(name)
			if isinstance(obj, Mapping)
			else object.__getattribute__(obj, name)
		)
	@staticmethod
	def getitem(obj: Any, name: str, _return = False):
		attr = None
		try:
			attr = Attrs._getitem(obj, name)
		except (AttributeError, KeyError) as e:
			if not _return:
				print(e)
				sys.exit(1)
			return Param.DEFAULT
		return attr
	@staticmethod
	def setitem(obj: Any, name: str, value: Any):
		(
			obj.__setitem__(name, value)
			if isinstance(obj, MutableMapping)
			else obj.__setattr__(name, value)
		)
	@staticmethod
	def has(obj: Any, name: str) -> bool:
		"""
		Check if obj has attr with `name`.
		Evaluates to the same operation as below expression
		except it uses object.__getattribute__ to avoid recursion.
		`return hasattr(obj, name) and getattr(obj, name) != None`
		"""
		attr = Attrs.getitem(obj, name, _return = True)
		return attr != None
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
		self._src_getfunc = getfunc(src)
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
				src_val = self._src_getfunc(self.callback_name(name))
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
		self._dst_setfunc = setfunc(dst)
		for name in self.iterable:
			src_val = self._src_getfunc(self.callback_name(name))
			if self.condition_val(src_val):
				self._dst_setfunc(name, self.callback_val(src_val))
	def get_notnone(
		self,
		src: Any,
	):
		return self._with_notnone().get(src)
	def set_notnone(
		self,
		src: Any,
		dst: Any,
	):
		return self._with_notnone().set(src, dst)
	def has_all_any(
		self,
		obj: Union[Any, Container],
		all_any: Union[str, bool] = "all",
		_return = True,
	):
		"""
		Checks if `obj` has all atrributes in its `iterable` property.
		"""
		if all_any == "all":
			all_any = True
		elif all_any == "any":
			all_any = False
		elif not isinstance(all_any, bool):
			raise InvalidType("all_any", all_any, ("all", "any"))
		_hasattrs = all_any
		def break_condition(attr):
			return (
				(all_any and not Attrs.has(obj, attr)) or #all
				(not all_any and Attrs.has(obj, attr)) #any
			)
		for attr in self.iterable:
			if break_condition(attr):
				break
		if _return:
			return _hasattrs
		if not _hasattrs:
			raise InvalidAttr(obj, self.iterable, "and" if all_any else "or")
	def set_check(
		self,
		src: Union[Any, Collection],
		dst: Any,
		*has_args,
		**has_kwargs,
	):
		"""
		Checks to see if the elements copied successfully.
		"""
		self.set(src, dst)
		self.has_all_any(dst, *has_args, **has_kwargs)

def stringify_map(map: Mapping):
	return stringify([f"{k}={v}" for k, v in map.items()])
def stringify(items: Union[Any, Sequence], and_or: str = ","):
	if not isinstance(items, Sequence) or isinstance(items, str):
		items = (items,)
	and_or_str = ", " if and_or == "," else f" {and_or} "
	return ", ".join(items[:-1]) + f"{and_or_str}{items[-1]}"
def isneg(res):
	return isinstance(res, bool) and not res

def tabbed_print(depth: int, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
def xnor(a:bool,b:bool):
	return (a and b) or (not a and not b)
