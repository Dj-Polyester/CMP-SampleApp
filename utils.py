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
	def break_condition(self):
		return self.exists()
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
		_default_props = self.default_props("all")
		_common_props = self.common_props("all",common_kwargs=kwargs)
		self._props = {**_default_props, **_common_props}
		self._check_type()
		Attrs().set_check(
			self._props,
			self,
			_return = False,
		)
	def is_equal(self, other: 'Config'):
		return self._props == other._props
	def _check_type(self):
		_all_params = self.all_params()
		for varname, var in self._props.items():
			param = _all_params[varname]
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
	) -> str:
		if s1 == Param.DEFAULT: s1 = cls.SUBSTR
		if s2 == Param.DEFAULT: s2 = cls.SUBSTR
		return add_str(
			s1,
			s2,
			reverse,
		)
	def default_params(self, *args, **kwargs):
		return self.typedparams(*args, _subtype = "default", **kwargs)
	def common_params(self, *args, **kwargs):
		return self.typedparams(*args, _subtype = "common", **kwargs)
	def params(self, *args, **kwargs):
		return self.typedparams(*args, **kwargs)
	def all_params(self, *args, **kwargs):
		return self.typedparams("all", *args, **kwargs)
	def valid_params(self, *args, **kwargs):
		return self.typedparams("valid", *args, **kwargs)
	def other_params(self, *args, **kwargs):
		return self.typedparams("other", *args, **kwargs)

	def default_props(self, *args, **kwargs):
		return self.typedprops(*args, _subtype = "default", **kwargs)
	def common_props(self, *args, **kwargs):
		return self.typedprops(*args, _subtype = "common", **kwargs)
	def props(self, *args, **kwargs):
		return self.typedprops(*args, **kwargs)
	def all_props(self, *args, **kwargs):
		return self.typedprops("all", *args, **kwargs)
	def valid_props(self, *args, **kwargs):
		return self.typedprops("valid", *args, **kwargs)
	def other_props(self, *args, **kwargs):
		return self.typedprops("other", *args, **kwargs)

	def vars(
		self,
		_basename: str,
		_type: str = "",
		_subtype: str = "",
		common_kwargs: Optional[Mapping] = Param.DEFAULT,
		var_callback: Callable = Param.DEFAULT,
	):
		if var_callback == Param.DEFAULT:
			var_callback = Attrs.getitem(self, f"_{_basename}_callback")
		vars_name = self._get_name(_type, _subtype, _basename)
		if _subtype != "common" and Attrs.has(self, vars_name):
			return Attrs.getitem(self, vars_name)
		_vars = var_callback(_type, _subtype, common_kwargs)
		Attrs.setitem(type(self), vars_name, _vars)
		return Attrs.getitem(self, vars_name)
	@staticmethod
	def _common_params_helper(params: Mapping, kwargs: Mapping):
		common_keys = params.keys() & kwargs.keys()
		return {k: params[k] for k in common_keys}
	@staticmethod
	def _common_kwargs_helper(params: Mapping, kwargs: Mapping):
		common_keys = params.keys() & kwargs.keys()
		return {k: kwargs[k] for k in common_keys}
	@staticmethod
	def _get_name(
		_type: str,
		_subtype: str,
		_basename: str,
	):
		type_placeholder = "" if _type == "current" else _type
		return add_strs(
			"",
			type_placeholder,
			_subtype,
			_basename,
			_lstrip_at_the_end = False,
		)
	@staticmethod
	def c(_c: Callable, p: Any):
		if not isinstance(p, str) and isinstance(p, Iterable):
			return _c(*p)
		return _c(p)
	@staticmethod
	def ret_mapping(
		_seq: Iterable,
		_filter: Callable,
		_callback_k: Callable,
		_callback_v: Callable,
	):
		_dic = {
			Config.c(_callback_k, args): Config.c(_callback_v, args)
			for args in _seq if Config.c(_filter, args)
		}
		return _dic
	@staticmethod
	def _current_type(_type:str):
		return _type == "" or _type == "current"
	def _params_callback(
		self,
		_type: str = "",
		_subtype: str = "",
		common_kwargs: Optional[Mapping] = Param.DEFAULT,
	):
		_seq, _map = Param.DEFAULT, Param.DEFAULT
		_callback_k = lambda *args: args[0]
		_callback_v = lambda *args: args[1] if len(args) == 2 else args[0]
		_filter = lambda *_: True
		if _type == "valid":
			_map = self.VALID_PARAMS
			_callback_k = lambda k,_: self.str_func(k, self.SUBSTR)
		elif _type == "other":
			_map = self.PARAMS
		elif _type == "all":
			_map = {**self.PARAMS, **self.valid_params()}
		elif Config._current_type(_type):
			_map = self._props
			_callback_v = lambda k, _: self.all_params()[k]
		else:
			raise InvalidVal("_type", _type, ("valid", "other", "all"))
		_seq = _map.items()
		_tmpparams = Config.ret_mapping(
			_seq,
			_filter,
			_callback_k,
			_callback_v,
		)
		_callback_k = lambda *args: args[0]
		_callback_v = lambda *args: args[1] if len(args) == 2 else args[0]
		if _subtype == "common":
			if isinstance(common_kwargs, Mapping):
				_seq = _tmpparams.keys() & common_kwargs.keys()
				_callback_v = lambda k: _tmpparams[k]
			else:
				raise InvalidType("common_kwargs", common_kwargs, Mapping)
		else:
			_seq = _tmpparams.items()
			if _subtype == "default":
				_filter = lambda _,v: v.default != Param.DEFAULT
			elif _subtype != "":
				raise InvalidVal("_subtype", _subtype, ("common", "default", ""))
		return Config.ret_mapping(
			_seq,
			_filter,
			_callback_k,
			_callback_v,
		)
	def typedparams(self,*args, **kwargs) -> Mapping[str, Param]:
		return self.vars("params", *args, **kwargs)
	def _props_callback(
		self,
		_type: str = "",
		_subtype: str = "",
		common_kwargs: Optional[Mapping] = Param.DEFAULT,
	):
		_map = self.typedparams(_type, _subtype, common_kwargs)
		_seq = _map.keys()
		_callback_k = lambda *args: args[0]
		_callback_v = lambda *args: self._props[args[0]]
		_filter = lambda *args: args[0] in self._props
		if _subtype == "common":
			if isinstance(common_kwargs, Mapping):
				_callback_v = lambda k: common_kwargs[k]
				_filter = lambda k: k in common_kwargs
			else:
				raise InvalidType("common_kwargs", common_kwargs, Mapping)
		else:
			_seq = _map.items()
			if _subtype == "default":
				_callback_v = lambda _, v: v.default
				_filter = lambda _, __: True
			elif _subtype != "":
				raise InvalidVal("_subtype", _subtype, ("common", "default", ""))

		return Config.ret_mapping(
			_seq,
			_filter,
			_callback_k,
			_callback_v,
		)
	def typedprops(self,*args, **kwargs) -> Mapping[str, Param]:
		return self.vars("props", *args, **kwargs)

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
	def props(self, config: Config, *args, **kwargs):
		return {
			k: getattr(self, k) for k in config.typedparams(*args, **kwargs).keys()
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
		attr = Param.DEFAULT
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
			else setattr(obj, name, value)
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
def _return_stripped(
	_str,
	delim: str = "_",
	_rstrip: bool = True,
	_lstrip: bool = True,
	_strip_str: Optional[str] = Param.DEFAULT,
):
	if _strip_str == Param.DEFAULT:
		_strip_str = f" {delim}"
	if _rstrip:
		_str = _str.rstrip(_strip_str)
	if _lstrip:
		_str = _str.lstrip(_strip_str)
	return _str

def add_strs(
	*strs: str,
	_lstrip_at_the_end: bool = True,
	_rstrip_at_the_end: bool = True,
	_reverse_iter: bool = True,
	**kwargs,
):
	_start_index = 0
	_end_index = -1
	_callback = lambda k: k
	if _reverse_iter:
		_start_index, _end_index = _end_index, _start_index
		_callback = lambda k: reversed(k)
	def str_args(s1, s2):
		return (s2, s1) if _reverse_iter else (s1, s2)
	_str = strs[_start_index]
	for __str in _callback(strs[1:-1]):
		_str = add_str(*str_args(_str, __str), **kwargs)
	new_kwargs = {
		**kwargs,
		"_lstrip": _lstrip_at_the_end,
		"_rstrip": _rstrip_at_the_end,
	}
	_str = add_str(*str_args(_str, strs[_end_index]), **new_kwargs)
	return _str
def add_str(
	s1: str,
	s2: str,
	reverse: bool = False,
	delim: str = "_",
	_rstrip: bool = True,
	_lstrip: bool = True,
	_strip_str: Optional[str] = Param.DEFAULT,
) -> str:
	_start, _end = (s2, s1) if reverse else (s1, s2)
	_str = f"{_start}{delim}{_end}"
	return _return_stripped(
		_str,
		delim,
		_rstrip,
		_lstrip,
		_strip_str,
	)
def print_equal(val1, val2, pretxt, _assert=True):
	is_equal = val1 == val2
	print(
		f"{pretxt} {Result(int(not is_equal)).status_msg()}"
	)
	if _assert:
		assert is_equal
if __name__ == "__main__":
	from test import Test
	class UtilsTest(Test):
		def config_test(self):
			class DummyClass: pass
			class DummyConfig(Config):
				PARAMS = {
					"param1": Param(type, repr = lambda x: x.__name__),
					"param2": Param(int),
					"param3": Param(int, 42),
				}
				VALID_PARAMS = {
					"param1": Param(bool),
					"param2": Param(str, "append"),
				}
				SUBSTR = "valid"
				@classmethod
				def str_func(cls, k, substr: Optional[str] = Param.DEFAULT):
					return cls._str_func(k, substr)
				def print(self, _raise = True):
					_params = {
						"_type": ["all", "valid", "other"],
						"_subtype": ["", "default", "common"],
						"_basename": ["params", "props"],
						"common_kwargs": [
							{
								"param1": DummyClass,
								"param1_valid": False,
							},
							Param.DEFAULT,
						],
					}
					def _condition(_subtype, common_kwargs, **kwargs):
						return not (
							_subtype == "common" and not isinstance(
								common_kwargs, Mapping
							)
						)
					for _param in product_dict(_params, _condition):
						common_kwargs = _param.pop("common_kwargs")
						_name = self._get_name(**_param)
						print(f"{_name} with {common_kwargs}")

						try:
							val1 = self.vars(
								common_kwargs=common_kwargs,
								**_param,
							)
							print(val1)
							val2 = getattr(self, _name)
							print(val2)
							print_equal(val1, val2, "Values", True)
						except BaseException:
							if _raise:
								raise
							print(Result(1).status_msg())
						print()

			dc1 = DummyConfig(param1=DummyClass, param2_valid="n8n")
			dc2 = DummyConfig(param2=31, param1_valid=True)
			print("dc1")
			dc1.print()
			print("dc2")
			dc2.print()
	utils_test = UtilsTest()
	utils_test()
