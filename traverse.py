from typing import Any, Callable, Optional
from collections import deque
from utils import exists, setattrs, hasattrs, stringify
from dataclasses import dataclass, field

@dataclass
class TraverseContainerConfig:
	_type: type
	top_index: int
	pop_func: str
	add_single_func: str = "append"
	add_multiple_func: str = "extend"
class TraverseContainer:
	def __init__(self, config: TraverseContainerConfig):
		self.config = config
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
class TraverseTypeConfig:
	container: TraverseContainerConfig
	add_special_token_before: bool
	proc_fun: Callable

class Traverse:
	PRECONFIGS = {
		"bfs": TraverseTypeConfig(
			container = TraverseContainerConfig(deque, 0, "popleft"),
			add_special_token_before=False,
			proc_fun=lambda x: x,
		),
		"dfs": TraverseTypeConfig(
			container = TraverseContainerConfig(list, -1, "pop"),
			add_special_token_before=True,
			proc_fun=lambda x: reversed(x),
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
					_type=name,
					*setup_args,
					**setup_kwargs,
				)
			return _recurse
		else:
			raise AttributeError(f"{type(self)} object has no attribute {name}")
	def setup(
		self,
		_type: Optional[str] = None,
		config: Optional[TraverseTypeConfig] = None,
		special_token: Any = None,
		**callbacks: Callable,
	):
		# Config
		if _type != None:
			self.config = Traverse.PRECONFIGS[_type]
		elif config != None:
			self.config = config
		elif not exists(self, "config") or not isinstance(self.config, TraverseTypeConfig):
			raise ValueError("Either traverse type or config must be provided")
		# Container
		if not exists(self, "containercls"):
			self.containercls = TraverseContainer(self.config.container)
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
	def callback(parent, obj):
		parent_id = "" if parent == None else parent.id
		print(f"callback obj {parent_id} {obj.id}")
	def after(parent, obj):
		parent_id = "" if parent == None else parent.id
		print(f"after obj {parent_id} {obj.id}")
	def cleanup(parent, obj):
		parent_id = "" if parent == None else parent.id
		print(f"cleanup obj {parent_id} {obj.id}")

	class DummyBase(Traverse):
		def __init__(self, id, *children):
			self.id = id
			self.children = children
	class Dummy(DummyBase):
		def __call__(self):
			self.bfs(
				callback = callback,
				after = after,
				cleanup = cleanup,
			)

	class IDummy(DummyBase):
		@staticmethod
		def callback(parent, obj):
			parent_id = "" if parent == None else parent.id
			print(f"callback obj {parent_id} {obj.id}")
		@staticmethod
		def after(parent, obj):
			parent_id = "" if parent == None else parent.id
			print(f"after obj {parent_id} {obj.id}")
		@staticmethod
		def cleanup(parent, obj):
			parent_id = "" if parent == None else parent.id
			print(f"cleanup obj {parent_id} {obj.id}")
		def __call__(self):
			self.bfs()

	cls_name = Dummy
	print(cls_name.__name__)
	d = cls_name(
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
	)()
