from typing import Any, Callable, Optional, Union, Mapping
from collections import deque
from dataclasses import dataclass
from utils import (
	exists,
	setattrs,
	setattrs_notnone,
	setattrs_check,
	stringify,
	stringify_map,
	status_msg,
	Config,
	State,
	product_dict,
	InvalidType,
	InvalidValue,
)
from test import Test

StrConfNone = Optional[Union[str, Config]]

def set_configs(obj: Any, config: StrConfNone = None, **configs: StrConfNone):
	if config != None:
		configs["config"] = config
	def set_config(config: StrConfNone):
		if isinstance(config, str):
			return type(obj).PRECONFIGS[config]
		elif isinstance(config, Config):
			return config
		elif not exists(obj, "config"):
			raise InvalidType("Config", config, (str, Config))
	setattrs_notnone(configs, obj, callback_val = set_config)

class TraverseContainerConfig(Config):
	VALID_FUNCS = {
		"pop": None,
		"add_single": "append",
		"add_multiple": "extend",
	}
	def __init__(self, **kwargs):
		valid_funcs = {f"{k}_func": v for k, v in TraverseContainerConfig.VALID_FUNCS.items()}
		kwargs = {**valid_funcs, **kwargs}
		super().__init__(**kwargs)
	def __repr__(self):
		funcs = {
			f"{k}_func": getattr(self, f"{k}_func") for k in TraverseContainerConfig.VALID_FUNCS.keys()
		}
		kwargs = {
			"_type": self._type.__name__,
			"top_index": self.top_index,
			**funcs,
		}
		return f"TraverseContainerConfig({stringify_map(kwargs)})"
class TraverseContainer:
	"""
	Arguments for the configuration parameter:
		`_type (type)`: type of the container used such as deque or list
		`top_index (int)`: the index used in `top` method

		The following fields are name of the methods available
		for objects of type `_type` for which corresponding method is a placeholder for.
		`pop_func (str):` the `pop` method
		`add_single_func (str):` the `add_single` method
		`add_multiple_func (str):` the `add_multiple` method
	Given a configuration, the container class implements the following methods automatically:
		`__call__(self, items=None) -> TraverseContainer`: Adds given items to the container and
		implements the following methods returning the container
			`pop() -> Any`: remove and return the element
			`add_single(item: Any)`: Add a single item to the container
			`add_multiple(items: Collection[Any])`: Add multiple items to the container
		`top() -> Any`: only return the element at the index configured by `top_index`
		`empty() -> bool`: return if the container is empty
	"""
	PRECONFIGS = {
		"stack": TraverseContainerConfig(_type=list, top_index=-1, pop_func="pop"),
		"queue": TraverseContainerConfig(_type=deque, top_index=0, pop_func="popleft"),
	}
	def __init__(
		self,
		config: Union[str, TraverseContainerConfig],
	):
		set_configs(self, config)
	def setup(self, items=None):
		self._container = self.config._type() if items == None else self.config._type(items)
		setattrs(
			self.config,
			self,
			TraverseContainerConfig.VALID_FUNCS,
			callback_name = lambda name: f"{name}_func",
			callback_val = lambda val: getattr(self._container, val)
		)
	def __call__(self, items=None):
		container = TraverseContainer(self.config)
		container.setup(items)
		return container
	def empty(self):
		return not self._container
	def top(self):
		return self._container[self.config.top_index] if self._container else None
	def __repr__(self):
		return repr(self._container)

class TraverseTypeConfig(Config):
	VALID_CONTAINERS = {
		"container": None,
		"parent_container": None,
		"backtrack_container": "stack",
	}
	def __init__(self, **kwargs):
		kwargs = {**TraverseTypeConfig.VALID_CONTAINERS, **kwargs}
		super().__init__(**kwargs)

class TraverseStateConfig(Config):
	def __init__(
		self,
		special_token: Any = None,
		backward_mode: str = "backtrace",
		verbose: bool = False,
		**callbacks,
	):
		self.special_token = special_token
		self.backward_mode = backward_mode
		self.verbose = verbose
		self.callbacks = callbacks

@dataclass
class TraverseState(State):
	def __init__(
		self,
		config: Optional[TraverseStateConfig] = None,
		type_config: Optional[Union[str, TraverseTypeConfig]] = None,
		**containers,
	):
		setattrs_check(
			containers,
			self,
			Traverse.VALID_CONTAINER_NAMES,
		)
		self.setup(config, type_config)
	def setup(
		self,
		config: Optional[TraverseStateConfig] = None,
		type_config: Optional[Union[str, TraverseTypeConfig]] = None,
	):
		# Configs
		set_configs(
			self,
			config,
			type_config=type_config,
		)
	def pop(self, container_name: str):
		self.node = getattr(self, container_name).pop()
	def add_single(self, container_name: str, item: Optional[Any] = None):
		add_item = self.node if item == None else item
		getattr(self, container_name).add_single(add_item)
	def run(self, func_name: str, container_name_parent: str):
		self.success = getattr(self.config, func_name)(
			getattr(self, container_name_parent).top(),
			self.node,
		)
	def add_children(self):
		if self.type_config.add_special_token_before:
			self.add_single("container", self.config.special_token)
		if exists(self.node, "children"):
			children = self.node.children
			if isinstance(children, dict):
				children = children.values()
			self.container.add_multiple(self.type_config.proc_fun(children))
		if not self.type_config.add_special_token_before:
			self.add_single("container", self.config.special_token)
	def forward(self):
		self.pop("container")
		if self.node == self.config.special_token: # Processed all children
			self.pop("parent_container")
			self.run("node_after", "parent_container")
		else:
			self.add_children()
			self.run("node_init", "parent_container")
			self.add_single("parent_container")
			self.add_single("backtrack_container")
	def backward_container(self, container_name: str):
		self.pop(container_name)
		self.run("node_backward", container_name)
	def backward_parent(self):
		self.config.node_backward(self.node.parent, self.node)
		self.node = self.node.parent
	def print(self):
		if self.config.verbose:
			print(self)

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
	VALID_CALLBACKS = (
		"node_init",
		"node_after",
		"node_backward",
	)
	VALID_BACKWARD_MODES = (
		"backtrace",
		"parent",
		"parent_dfs",
	)
	VALID_CONTAINER_NAMES = (
		"container",
		"parent_container",
		"backtrack_container",
	)
	def setup(self, config: Union[str, TraverseTypeConfig]):
		# Configs
		set_configs(self, config)
		# Containers
		if not exists(self, "containercls"):
			_c = self.config.container
			_pc = self.config.parent_container
			self.containercls = TraverseContainer(_c)
			self.parent_containercls = TraverseContainer(_c) if _pc==None else TraverseContainer(_pc)
			self.backtrack_containercls = TraverseContainer(self.config.backtrack_container)
		# Callbacks
		setattrs_check(
			self.config.callbacks,
			self,
			Traverse.VALID_CALLBACKS,
		)
	def __getattr__(self, name: str):
		if name in Traverse.PRECONFIGS:
			def _recurse(
				state_config: TraverseStateConfig,
				obj: Optional[Any] = None,
			):
				self.recurse(
					state_config=state_config,
					type_config=name,
					obj=obj,
				)
			return _recurse
		elif exists(self, "state") and exists(self.state, name):
			return getattr(self.state, name)
		else:
			raise AttributeError(f"{type(self)} object has no attribute {name}")
	def print(self, *args, **kwargs):
		if exists(self, "verbose") and self.verbose:
			print(*args, **kwargs)
	def recurse(
		self,
		state_config: TraverseStateConfig,
		type_config: Union[str, TraverseTypeConfig],
		obj: Optional[Any] = None,
	):
		self.setup(type_config)
		if obj == None:
			obj = self
		self.state = TraverseState(
			container = self.containercls([obj]),
			parent_container = self.parent_containercls(),
			backtrack_container = self.backtrack_containercls(),
			config = state_config,
			type_config = type_config,
		)
		self.state.print()
		while not self.state.container.empty():
			self.forward()
			self.state.print()
			if self.state.failed(): break
		return self.state
	def recurse_backward(self):
		self.state.print()
		if self.state.config.backward_mode == "backtrace":
			while not self.state.backtrack_container.empty():
				self.state.backward_container("backtrack_container")
				self.state.print()
		elif self.state.config.backward_mode == "parent":
			while exists(self.state.node, "parent"):
				self.state.backward_parent()
				self.state.print()
		elif self.state.config.backward_mode == "parent_dfs":
			while not self.state.backtrack_container.empty():
				self.state.backward_container("parent_container")
				self.state.print()
		else:
			raise InvalidValue(
				"Backward mode",
				self.state.config.backward_mode,
				Traverse.VALID_BACKWARD_MODES,
			)

if __name__ == "__main__":
	def callbacktxt(prefix, parent, obj):
		parent_id = "" if parent == None else parent.id
		_callbacktxt = f"{prefix} {parent_id} {obj.id}"
		DummyBase.buffertxt.append(_callbacktxt)
		print(_callbacktxt)
	def node_init(*args):
		callbacktxt("node_init", *args)
		if args[1].id == 5:
			return False
	def node_after(*args):
		callbacktxt("node_after", *args)
	def node_backward(*args):
		callbacktxt("node_backward", *args)

	class DummyBase(Traverse):
		buffertxt: list
		def __init__(self, id, *children):
			DummyBase.buffertxt = []
			self.id = id
			self.set_children(children)
		def set_children(self, children):
			self.children = children
			for child in self.children:
				child.parent = self
		def __repr__(self):
			return str(self.id)
	class Dummy(DummyBase):
		def __call__(self, _type, state_config):
			getattr(self, _type)(
				state_config = state_config
			)

	class IDummy(DummyBase):
		@staticmethod
		def node_init(*args):
			return node_init(*args)
		@staticmethod
		def node_after(*args):
			return node_after(*args)
		@staticmethod
		def node_backward(*args):
			return node_backward(*args)
		def __call__(self, _type, backward_mode):
			getattr(self, _type)(backward_mode = backward_mode)

	class TraverseTest(Test):
		def containers(self):
			params = {
				"container_config" : [
					"stack",
					"queue",
					TraverseContainerConfig(_type=deque, top_index=0, pop_func="popleft"),
				],
				"items": [
					[31, 69],
					[],
				]
			}

			for i, config in enumerate(product_dict(params), 1):
				container_cls = TraverseContainer(config["container_config"])
				container = container_cls(config["items"])
				print(f"Container {i}")
				print(f"Config: {config}")
				print(container)
				if container.empty():
					print("Container is empty")
				else:
					print(
f"""Container is not empty
Top value at index {container.config.top_index} is {container.top()}
Container after popping {container.pop()}: {container}
"""					)
				_item = 42
				container.add_single(_item)
				print(f"Container after adding {_item}: {container}")
				_items = [29, 86]
				container.add_multiple(_items)
				print(f"Container after adding {_items}: {container}\n")


		def compare_implementations(self):
			buffer_txts = []
			params = {
				"_type": Traverse.PRECONFIGS.keys(),
				"backward_mode": Traverse.VALID_BACKWARD_MODES,
			}
			cls_types = [
				Dummy,
				IDummy,
			]
			cls_names = [t.__name__ for t in cls_types]
			for param in product_dict(params):
				print(f"Parameters: {param}")
				for cls_type, cls_name in zip(cls_types, cls_names):
					print(f"Class name: {cls_name}")
					cls_type(
						1,
						cls_type(
							2,
							cls_type(
								4
							),
							cls_type(
								5
							),
						),
						cls_type(
							3,
							cls_type(
								6
							),
							cls_type(
								7
							),
						),
					)(**param)
					buffer_txts.append(DummyBase.buffertxt)
				is_equal = buffer_txts[0] == buffer_txts[1]
				print(
					f"\n{stringify(cls_names)} {status_msg(int(not is_equal))}"
				)
				assert is_equal
	test=TraverseTest()
	test.containers()
