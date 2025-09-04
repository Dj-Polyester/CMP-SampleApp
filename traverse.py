from typing import Any, Callable, Optional, Union
from collections import deque
from dataclasses import dataclass
from utils import exists, setattrs, hasattrs, stringify, status_msg
from test import Test

class Config: pass

def set_config(obj: Any, config: Union[str, Config]):
	if isinstance(config, str):
		obj.config = type(obj).PRECONFIGS[config]
	elif isinstance(config, Config):
		obj.config = config
	elif not exists(obj, "config"):
		raise TypeError(f"Config has type {type(config)}")

@dataclass
class TraverseContainerConfig(Config):
	_type: type
	top_index: int
	pop_func: str
	add_single_func: str = "append"
	add_multiple_func: str = "extend"
class TraverseContainer:
	PRECONFIGS = {
		"stack": TraverseContainerConfig(list, -1, "pop"),
		"queue": TraverseContainerConfig(deque, 0, "popleft"),
	}
	def __init__(
		self,
		config: Union[str, TraverseContainerConfig],
	):
		set_config(self, config)
	def setup(self, args=None):
		self._container = self.config._type() if args == None else self.config._type(args)
		self.pop = getattr(self._container, self.config.pop_func)
		self.add_single = getattr(self._container, self.config.add_single_func)
		self.add_multiple = getattr(self._container, self.config.add_multiple_func)
	def __call__(self, args=None):
		container = TraverseContainer(self.config)
		container.setup(args)
		return container
	def empty(self):
		return not self._container
	def top(self):
		return self._container[self.config.top_index] if self._container else None

@dataclass
class TraverseTypeConfig(Config):
	add_special_token_before: bool
	proc_fun: Callable
	container: Union[str, TraverseContainerConfig]
	parent_container: Union[str, TraverseContainerConfig] = "stack"

class Traverse:
	PRECONFIGS = {
		"bfs": TraverseTypeConfig(
			add_special_token_before=False,
			proc_fun=lambda x: x,
			container = "queue",
		),
		"dfs": TraverseTypeConfig(
			add_special_token_before=True,
			proc_fun=lambda x: reversed(x),
			container = "stack",
		),
	}
	VALID_CALLBACKS = [
		"callback",
		"after",
		"cleanup",
	]
	def __getattr__(self, name: str):
		if name in Traverse.PRECONFIGS:
			def _recurse(
				obj: Optional[Any] = None,
				*setup_args,
				**setup_kwargs,
			):
				self.recurse(
					obj,
					config=name,
					*setup_args,
					**setup_kwargs,
				)
			return _recurse
		else:
			raise AttributeError(f"{type(self)} object has no attribute {name}")
	def setup(
		self,
		config: Union[str, TraverseTypeConfig],
		special_token: Any = None,
		**callbacks: Callable,
	):
		# Config
		set_config(self, config)
		# Containers
		if not exists(self, "containercls"):
			self.containercls = TraverseContainer(self.config.container)
			self.parent_containercls = TraverseContainer(self.config.parent_container)
		# Special token
		self.special_token = special_token
		# Callbacks
		self.callbacks = callbacks
		setattrs(self.callbacks, self)
		if not hasattrs(self, self.VALID_CALLBACKS):
			raise AttributeError(
				f"Object should implement {stringify(Traverse.VALID_CALLBACKS)}"
			)

	def recurse(
		self,
		obj: Optional[Any] = None,
		*setup_args,
		**setup_kwargs,
	):
		self.setup(*setup_args, **setup_kwargs)
		if obj == None:
			obj = self
		container = self.containercls([obj])
		parent_container = self.containercls()
		def _neg(res):
			return isinstance(res, bool) and not res
		success = False
		node = None
		while not container.empty():
			node = container.pop()
			if node == self.special_token: # Processed all children
				node = parent_container.pop()
				success = self.after(parent_container.top(), node)
			else:
				if self.config.add_special_token_before:
					container.add_single(self.special_token)
				if exists(node, "children"):
					children = node.children.values() if isinstance(node.children, dict) else node.children
					container.add_multiple(self.config.proc_fun(children))
				if not self.config.add_special_token_before:
					container.add_single(self.special_token)
				parent_node = parent_container.top()
				parent_container.add_single(node)
				success = self.callback(parent_node, node)
			if _neg(success):
				break
		while not parent_container.empty():
			self.cleanup(parent_container.top(), node)
			node = parent_container.pop()

if __name__ == "__main__":
	def callbacktxt(prefix, parent, obj):
		parent_id = "" if parent == None else parent.id
		_callbacktxt = f"{prefix} {parent_id} {obj.id}"
		DummyBase.buffertxt.append(_callbacktxt)
		print(_callbacktxt)
	def callback(*args):
		callbacktxt("callback", *args)
	def after(*args):
		callbacktxt("after", *args)
	def cleanup(*args):
		callbacktxt("cleanup", *args)

	class DummyBase(Traverse):
		buffertxt: list
		def __init__(self, id, *children):
			DummyBase.buffertxt = []
			self.id = id
			self.children = children
	class Dummy(DummyBase):
		def __call__(self, _type):
			getattr(self, _type)(
				callback = callback,
				after = after,
				cleanup = cleanup,
			)

	class IDummy(DummyBase):
		@staticmethod
		def callback(*args):
			callbacktxt("callback", *args)
		@staticmethod
		def after(*args):
			callbacktxt("after", *args)
		@staticmethod
		def cleanup(*args):
			callbacktxt("cleanup", *args)
		def __call__(self, _type):
			getattr(self, _type)()

	class TraverseTest(Test):
		def compare_implementations(self):
			buffer_txts = []
			_types = Traverse.PRECONFIGS
			cls_names = [
				Dummy,
				IDummy,
			]
			cls_names_str = [t.__name__ for t in cls_names]
			for _type in _types:
				for cls_name, cls_name_str in zip(cls_names, cls_names_str):
					print(f"\n{cls_name_str} {_type}")
					cls_name(
						1,
						cls_name(
							2,
							cls_name(
								4
							),
							cls_name(
								5
							),
						),
						cls_name(
							3,
							cls_name(
								6
							),
							cls_name(
								7
							),
						),
					)(_type)
					buffer_txts.append(DummyBase.buffertxt)
				is_equal = buffer_txts[0] == buffer_txts[1]
				print(
					f"\n{stringify(cls_names_str)} {_type} {status_msg(int(not is_equal))}"
				)
				assert is_equal
	test=TraverseTest()
	test()
