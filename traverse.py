from typing import Any, Callable, Optional, Union, Mapping
from collections import deque
from dataclasses import dataclass
from utils import (
	exists,
	setattrs,
	setattrs_notnone,
	setattrs_check,
	hasattrs,
	stringify,
	stringify_map,
	status_msg,
	Config,
	State,
	product_dict,
	InvalidType,
	InvalidValue,
	TraversalUtils,
)
from test import Test

class TraverseContainerConfig(Config):
	"""
	Arguments:
		`_type (type)`: type of the container used such as `deque` or `list`
		`top_index (int)`: the index used in `top` method

		The following fields are name of the methods available
		for objects of type `_type` for which corresponding method is a placeholder for.

		`pop_func (str):` the `pop` method
		`add_single_func (str):` the `add_single` method
		`add_multiple_func (str):` the `add_multiple` method
	"""
	PARAMS = {
		"_type": Config.Param(type, repr = lambda x: x.__name__),
		"top_index": Config.Param(int),
	}
	VALID_PARAMS = {
		"pop": Config.Param(str),
		"add_single": Config.Param(str, default = "append"),
		"add_multiple": Config.Param(str, default = "extend"),
	}
	@classmethod
	def str_func(cls, k):
		return f"{k}_func"

class TraverseTypeConfig(Config):
	"""
	Arguments:
		`proc_children (Callable)`: callable to process children before adding them to container
		`special_token_before_children (bool)`: whether to add the special token before children.
		True for FILO containers and False for FIFO containers is preferable.

		The following fields are name of the containers for specific purposes.
		The current node is accessed via `pop` or `top` operation on the container.

		`container (str | TraverseContainerConfig)`: Keeps track of nodes executed in order.
		Gives the current node to be processed.
		`parent_container (str | TraverseContainerConfig)`: Gives the parent of the nodes
		in the `container` until the `special_token`.
		`backtrack_container (str | TraverseContainerConfig)`: Keeps track of past nodes.
		Simulates a roll-back operation, gives the node in the reverse order of nodes
		given by `container`.
	"""
	PARAMS = {
		"proc_children": Config.Param(
			Callable,
			repr = lambda x: x.__name__,
		),
		"special_token_before_children": Config.Param(bool),
	}
	VALID_PARAMS = {
		"_": Config.Param(Union[str, TraverseContainerConfig]),
		"parent": Config.Param(Union[str, TraverseContainerConfig]),
		"backtrack": Config.Param(Union[str, TraverseContainerConfig], "stack"),
	}
	@classmethod
	def str_func(cls, k):
		return "container" if k=="_" else f"{k}_container"

class TraverseStateConfig(Config):
	"""
	Arguments:
		`special_token (Any)`: This token is popped when all children are processed
		`backward_mode (str)`: Decides on the roll-back method.
		Valid attributes are in the `VALID_BACKWARD_MODES` variable. "backtrace" and "parent"
		uses `backtrack_container` and `parent_container` respectively. "parent_pointer"
		looks for a `parent` property for each node
		and follows the path until the property cannot be found.
		`verbose (bool)`: Verbosity

		The following fields are name of the callback methods for specific purposes

		`node_init (Callable)`: Called on a node when its children are added
		`node_finalize (Callable)`: Called on a node when its children are processed and
	the `special_token` is encountered
		`node_cleanup (Callable)`: Called on the nodes in the order specified by `backward_mode`
	"""
	VALID_BACKWARD_MODES = {
		"backtrace": "backtrack",
		"parent": "parent",
		"parent_pointer": None,
	}
	PARAMS = {
		"special_token": Config.Param(...),
		"backward_mode": Config.Param(str, "backtrace"),
		"verbose": Config.Param(bool, False),
	}
	VALID_PARAMS = {
		"init": Config.Param(Callable),
		"finalize": Config.Param(Callable),
		"cleanup": Config.Param(Callable),
	}
	def backward_container(self):
		bm = self.VALID_BACKWARD_MODES[
			self.backward_mode
		]
		if bm != None:
			return True, self.str_func(bm)
		return False, self.backward_mode
	@classmethod
	def str_func(cls, k):
		return f"node_{k}"

class TraverseContainer(TraversalUtils):
	"""
	Given a configuration, the container class implements the following methods automatically:
		`__call__(self, items=None) -> TraverseContainer`: Adds given items to the container and
		implements the following methods returning the container
			`pop() -> Any`: Remove and return the element
			`add_single(item: Any)`: Add a single item to the container
			`add_multiple(items: Collection[Any])`: Add multiple items to the container
		`top() -> Any`: Return the element at the index configured by `top_index`
		`empty() -> bool`: Return if the container is empty
	"""
	PRECONFIGS = {
		"stack": TraverseContainerConfig(_type=list, top_index=-1, pop_func="pop"),
		"queue": TraverseContainerConfig(_type=deque, top_index=0, pop_func="popleft"),
	}
	def setup(self, config: Union[str, TraverseContainerConfig]):
		self.set_configs(config)
	def _setup(self, items=None):
		self._container = self.config._type() if items == None else self.config._type(items)
		setattrs(
			self.config,
			self,
			TraverseContainerConfig.VALID_PARAMS,
			callback_name = lambda name: f"{name}_func",
			callback_val = lambda val: getattr(self._container, val)
		)
	def __call__(self, items=None):
		container = TraverseContainer(self.config)
		container._setup(items)
		return container
	def empty(self):
		return not self._container
	def top(self):
		return self._container[self.config.top_index] if self._container else None
	def __repr__(self):
		return repr(self._container)

class TraverseState(TraversalUtils, State):
	PRECONFIGS = {
		"bfs": TraverseTypeConfig(
			special_token_before_children=False,
			proc_children=lambda x: x,
			container = "queue",
		),
		"dfs": TraverseTypeConfig(
			special_token_before_children=True,
			proc_children=lambda x: reversed(x),
			container = "stack",
		),
	}
	def setup(
		self,
		config: Optional[TraverseStateConfig] = None,
		type_config: Optional[Union[str, TraverseTypeConfig]] = None,
		**containers,
	):
		# Configs
		self.set_configs(
			config,
			type_config=type_config,
		)
		# Containers
		_hasattrs = hasattrs(
			containers,
			TraverseTypeConfig.valid_keys(),
		)
		if not _hasattrs:
			_c = self.type_config.container
			_pc = self.type_config.parent_container
			_containercls = {
				"containercls" : TraverseContainer(_c),
				"parent_containercls" : TraverseContainer(_c) if _pc==None else TraverseContainer(_pc),
				"backtrack_containercls" : TraverseContainer(self.type_config.backtrack_container),
			}
			_containers = dict(
				zip(self.type_config.valid_keys(), _containercls.values())
			)
			containers = {**_containers, **containers}
		setattrs_check(
			containers,
			self,
			TraverseTypeConfig.valid_keys(),
			_return = False,
		)

	def _container(self, name: str):
		return getattr(self, name)
	def _callback(self, name: str):
		return getattr(self.type_config, name)
	def pop(self, container_name: str):
		self.node = self._container(container_name).pop()
	def add_single(self, container_name: str, item: Optional[Any] = None):
		add_item = self.node if item == None else item
		self._container(container_name).add_single(add_item)
	def run(self, func_name: str, container_name_parent: str):
		self.success = self._callback(func_name)(
			self._container(container_name_parent).top(),
			self.node,
		)
	def add_children(self):
		if self.type_config.special_token_before_children:
			self.add_single("container", self.config.special_token)
		if exists(self.node, "children"):
			children = self.node.children
			if isinstance(children, dict):
				children = children.values()
			self.container.add_multiple(self.type_config.proc_children(children))
		if not self.type_config.special_token_before_children:
			self.add_single("container", self.config.special_token)
	def forward(self):
		self.pop("container")
		if self.node == self.config.special_token: # Processed all children
			self.pop("parent_container")
			self.run("node_finalize", "parent_container")
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

class Traverse(TraversalUtils):
	def setup(
		self,
		state_config: Optional[TraverseStateConfig] = None,
		type_config: Optional[Union[str, TraverseTypeConfig]] = None,
	):
		# Configs
		self.set_configs(
			state_config=state_config,
			type_config=type_config,
		)
		# Containers
		_c = self.type_config.container
		_pc = self.type_config.parent_container
		self.containercls = TraverseContainer(_c)
		self.parent_containercls = TraverseContainer(_c) if _pc==None else TraverseContainer(_pc)
		self.backtrack_containercls = TraverseContainer(self.type_config.backtrack_container)
		# Callbacks
		_hasattrs = hasattrs(
			self.state_config,
			TraverseStateConfig.valid_keys(),
		)
		if not _hasattrs:
			setattrs_check(
				self,
				self.state_config,
				TraverseStateConfig.valid_keys(),
				_return = False,
			)

	def __getattr__(self, name: str):
		if exists(self, "state"):
			if name in self.state.PRECONFIGS:
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
			elif exists(self.state, name):
				return getattr(self.state, name)
		else:
			raise AttributeError(f"{type(self)} object has no attribute {name}")
	def recurse(
		self,
		state_config: TraverseStateConfig,
		type_config: Union[str, TraverseTypeConfig],
		obj: Optional[Any] = None,
	):
		self.setup(state_config, type_config)
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

		is_container, bm = self.state.config.backward_container()
		if is_container:
			while not getattr(self.state, bm).empty():
				self.state.backward_container(bm)
				self.state.print()
		elif self.state.config.backward_mode == "parent_pointer":
			while exists(self.state.node, "parent"):
				self.state.backward_parent()
				self.state.print()
		else:
			raise InvalidValue(
				"Backward mode",
				self.state.config.backward_mode,
				TraverseStateConfig.VALID_BACKWARD_MODES,
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
	def node_finalize(*args):
		callbacktxt("node_finalize", *args)
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
		def node_finalize(*args):
			return node_finalize(*args)
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
