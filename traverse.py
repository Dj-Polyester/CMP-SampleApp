from typing import Any, Callable, Optional, Union
from collections import deque
from utils import (
	exists,
	Attrs,
	stringify,
	stringify_map,
	status_msg,
	Config,
	Param,
	State,
	product_dict,
	InvalidVal,
	InvalidAttr,
	TraversalUtils,
)
from test import Test

class TraversalContainerConfig(Config):
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
		"_type": Param(type, repr = lambda x: x.__name__),
		"top_index": Param(int),
		"pop_backward_before_run": Param(bool, True),
	}
	VALID_PARAMS = {
		"pop": Param(str),
		"pop_backward": Param(str, "pop"),
		"add_single": Param(str, "append"),
		"add_multiple": Param(str, "extend"),
	}
	SUBSTR = "func"
	@classmethod
	def str_func(cls, k, substr: Optional[str] = Param.DEFAULT):
		return cls._str_func(k, substr)

class TraversalTypeConfig(Config):
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
		"proc_children": Param(
			Callable,
			repr = lambda x: x.__name__,
		),
		"special_token_before_children": Param(bool),
	}
	VALID_PARAMS = {
		"": Param(Union[str, TraversalContainerConfig]),
		"parent": Param(Union[str, TraversalContainerConfig, type(Param.NON_DEFAULT)], Param.NON_DEFAULT),
		"backtrack": Param(Union[str, TraversalContainerConfig], "stack"),
	}
	SUBSTR = "container"
	@classmethod
	def str_func(cls, k, substr: Optional[str] = Param.DEFAULT):
		return cls._str_func(k, substr)

class TraversalStateConfig(Config):
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
	PARAMS = {
		"name": Param(str),
		"special_token": Param(default = Param.NON_DEFAULT),
		"backward_mode": Param(str, "backtrace"),
		"verbose": Param(bool, False),
	}
	VALID_PARAMS = {
		"init": Param(
			Callable,
			lambda _, __:_,
		),
		"finalize": Param(
			Callable,
			lambda _, __:_,
		),
		"backward": Param(
			Callable,
			lambda _, __:_,
		),
	}
	VALID_BACKWARD_MODES = {
		"backtrace": "backtrack",
		"parent": "parent",
		"parent_pointer": Param.DEFAULT,
	}
	def backward_container(self):
		bm = self.VALID_BACKWARD_MODES[
			self.backward_mode
		]
		if bm != Param.DEFAULT:
			return True, TraversalTypeConfig.str_func(bm)
		return False, self.backward_mode
	SUBSTR = "node"
	@classmethod
	def str_func(cls, k, substr: Optional[str] = Param.DEFAULT):
		return cls._str_func(substr, k)

class TraversalContainer(TraversalUtils):
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
		"stack": TraversalContainerConfig(
			_type=list, top_index=-1, pop_func="pop",
		),
		"queue": TraversalContainerConfig(
			_type=deque, top_index=0, pop_func="popleft",
		),
	}
	def __getattr__(self, name: str):
		if name.startswith("is_"):
			name = name[3:]
			if name in self.PRECONFIGS:
				return self.config.is_equal(self.PRECONFIGS[name])
		else:
			raise InvalidAttr(self, name)
	def setup(self, config: Union[str, TraversalContainerConfig]):
		self.set_configs(config)

	def _setup(self, items= Param.DEFAULT):
		self._container = self.config._type() if items == Param.DEFAULT else self.config._type(items)
		def _callback_val(val: Union[str, Callable]):
			if isinstance(val, str):
				return getattr(self._container, val)
			elif isinstance(val, Callable):
				return val
			else:
				raise InvalidVal("val", val, (str, Callable))
		Attrs(
			TraversalContainerConfig.VALID_PARAMS,
			callback_name = lambda name: f"{name}_{TraversalContainerConfig.SUBSTR}",
			callback_val = _callback_val,
		).set(
			self.config,
			self,
		)
		pass
	def __call__(self, items= Param.DEFAULT):
		container = TraversalContainer(self.config)
		container._setup(items)
		return container
	def empty(self):
		return not self._container
	def top(self, backward: bool = False):
		ti = self.config.top_index
		if self.reverse and backward:
			if ti == 0:
				ti = -1
			elif ti == -1:
				ti = 0
			else:
				raise InvalidVal("top_index", ti, (0,-1))
		return self._container[ti] if self._container else Param.DEFAULT
	def __repr__(self):
		return repr(self._container)

class TraversalState(TraversalUtils, State):
	PRECONFIGS = {
		"bfs": TraversalTypeConfig(
			special_token_before_children=False,
			proc_children=lambda x: x,
			container = "queue",
		),
		"dfs": TraversalTypeConfig(
			special_token_before_children=True,
			proc_children=lambda x: reversed(x),
			container = "stack",
		),
	}
	def get_containers(self, *params):
		_c = self.type_config.container
		_pc = self.type_config.parent_container

		container_cls = (
			TraversalContainer(_c),
			TraversalContainer(_c) if _pc==Param.NON_DEFAULT else TraversalContainer(_pc),
			TraversalContainer(self.type_config.backtrack_container),
		)
		if len(params) > len(container_cls):
			raise ValueError(
				f"Length of parameters {len(params)}"
				f"has to be shorter than or equal to {len(container_cls)}"
			)
		return [
			container_cls[i](p) for i, p in enumerate(params)
		] + [
			c() for c in container_cls[len(params):]
		]
	def _config_containers(self, **containers):
		for name, container in containers.items():
			container.name = name
			container.reverse = not container.is_stack and "parent" in name
	def set_containers(
		self,
		**containers,
	):
		_valid_keys = TraversalTypeConfig.keys("valid")
		_hasattrs = Attrs().has(
			containers,
			_valid_keys,
		)
		if not _hasattrs:
			_containers = dict(
				zip(_valid_keys, self.get_containers())
			)
			containers = {**_containers, **containers}
		self._config_containers(**containers)

		attrs = Attrs(_valid_keys)
		attrs.set(
			containers,
			self,
		)
		attrs.has(
			self,
			_valid_keys,
			_return = False,
		)
	def setup(
		self,
		config: Optional[TraversalStateConfig] = Param.DEFAULT,
		type_config: Optional[Union[str, TraversalTypeConfig]] = Param.DEFAULT,
		**containers,
	):
		# Configs
		self.set_configs(
			config,
			type_config=type_config,
		)
		# Containers
		if containers != {}:
			self.set_containers(**containers)

	def _container(self, name: str):
		return getattr(self, name)
	def _callback(self, name: str):
		return getattr(self.config, name)
	def pop(self, container_name: str, backward:bool=False):
		popop = "pop_backward" if backward else "pop"
		self.node = getattr(self._container(container_name), popop)()
	def add_single(self, container_name: str, item: Optional[Any] = Param.DEFAULT):
		add_item = self.node if item == Param.DEFAULT else item
		self._container(container_name).add_single(add_item)
	def run(self, func_name: str, container_name_parent: str, backward:bool=False):
		self.success = self._callback(func_name)(
			self._container(container_name_parent).top(backward),
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
		container = self._container(container_name)
		if container.config.pop_backward_before_run:
			self.pop(container_name, True)
		self.run("node_backward", container_name, True)
		if not container.config.pop_backward_before_run:
			self.pop(container_name, True)
	def backward_parent(self):
		self.config.node_backward(self.node.parent, self.node)
		self.node = self.node.parent
	def print(self):
		if exists(self, "verbose") and self.verbose:
			print(self)
	def __repr__(self):
		_props = self.props(self.type_config, "valid")
		_other_props = ["success", "node"]
		for prop in _other_props:
			if exists(self, prop):
				_props[prop] = getattr(self, prop)
		return f"TraverseState({stringify_map(_props)})"
class Traversal(TraversalUtils):
	PRECONFIGS = TraversalState.PRECONFIGS
	def setup(
		self,
		state_config: Optional[TraversalStateConfig] = Param.DEFAULT,
		type_config: Optional[Union[str, TraversalTypeConfig]] = Param.DEFAULT,
	):
		self.state = TraversalState(state_config, type_config)
		# Callbacks
		state_config = self.state.config
		_valid_defaults = state_config.defaults("valid")
		attrs = Attrs(
			_valid_defaults.keys(),
			condition_name = lambda x: exists(state_config, x),
		)
		_valid_props = attrs.get(state_config)
		_self_props = attrs._with(
			_valid_defaults.keys(),
			condition_name = lambda x: exists(self, x),
			condition_val = lambda x: x != Param.DEFAULT,
		).get(self)
		_all_valid = {**_valid_defaults, **_valid_props, **_self_props}
		attrs._with().set(
			_all_valid,
			state_config,
		)
		attrs.has(
			state_config,
			TraversalStateConfig.keys("valid"),
			_return = False,
		)
		'''
		state_config = self.state.config
		_valid_keys = TraversalStateConfig.keys("valid")
		attrs = Attrs(iterable = _valid_keys)
		_hasattrs = attrs.has(
			state_config,
			_valid_keys,
		)
		if not _hasattrs:
			attrs.set(
				self,
				state_config,
			)
			attrs.has(
				state_config,
				_valid_keys,
				_return=False,
			)
		'''
	def __getattr__(self, name: str):
		if name in self.PRECONFIGS:
			def _recursive(
				state_config: TraversalStateConfig,
				obj: Optional[Any] = Param.DEFAULT,
			):
				return self.recursive(
					state_config=state_config,
					type_config=name,
					obj=obj,
				)
			return _recursive
		elif exists(self, "state"):
			return getattr(self.state, name)
		else:
			raise InvalidAttr(self, name)
	def recursive(
		self,
		state_config: TraversalStateConfig,
		type_config: Union[str, TraversalTypeConfig],
		obj: Optional[Any] = Param.DEFAULT,
	):
		self.setup(state_config, type_config)
		if obj == Param.DEFAULT:
			obj = self
		self.state.set_containers(
			**dict(
				zip(TraversalTypeConfig.keys("valid"), self.get_containers([obj]))
			)
		)
		self.state.print()
		while not self.state.container.empty():
			self.forward()
			self.state.print()
			if self.state.failed(): break
		return self.state
	def recursive_backward(self, backward_mode = Param.DEFAULT):
		if backward_mode != Param.DEFAULT:
			self.state.config.backward_mode = backward_mode
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
			self.config.node_backward(Param.DEFAULT, self.node)
			self.state.print()
		else:
			raise InvalidVal(
				"Backward mode",
				self.state.config.backward_mode,
				tuple(TraversalStateConfig.VALID_BACKWARD_MODES.keys()),
			)

if __name__ == "__main__":
	def callbacktxt(prefix, parent, obj):
		parent_id = "" if parent == Param.DEFAULT else parent.id
		_callbacktxt = f"{prefix} {parent_id} {obj.id}"
		DummyBase.buffertxt.append(_callbacktxt)
		print(_callbacktxt)
	def node_init(*args):
		callbacktxt("node_init", *args)
		if args[1].id == 6:
			return False
	def node_finalize(*args):
		callbacktxt("node_finalize", *args)
	def node_backward(*args):
		callbacktxt("node_backward", *args)

	class DummyBase(Traversal):
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
			return repr(self.id)
		def __call__(self):
			print("Forward:")
		def backward(self, state: State):
			print("Backward:")
			if state.failed():
				self.recursive_backward()
	class Dummy(DummyBase):
		def __call__(self, _type, backward_mode):
			super().__call__()
			state = getattr(self, _type)(
				state_config = TraversalStateConfig(
					node_init = node_init,
					node_finalize = node_finalize,
					node_backward = node_backward,
					backward_mode = backward_mode,
				)
			)
			self.backward(state)

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
			super().__call__()
			state = getattr(self, _type)(
				state_config = TraversalStateConfig(
					backward_mode = backward_mode,
				)
			)
			self.backward(state)

	class TraversalTest(Test):
		def containers(self):
			params = {
				"container_config" : [
					"stack",
					"queue",
					TraversalContainerConfig(_type=deque, top_index=0, pop_func="popleft"),
				],
				"items": [
					[31, 69],
					[],
				]
			}

			for i, config in enumerate(product_dict(params), 1):
				container_cls = TraversalContainer(config["container_config"])
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
				"_type": TraversalState.PRECONFIGS.keys(),
				"backward_mode": TraversalStateConfig.VALID_BACKWARD_MODES.keys(),
			}
			cls_types = [
				Dummy,
				IDummy,
			]
			cls_names = [t.__name__ for t in cls_types]
			for param in product_dict(params):
				print(f"\nParameters: {param}")
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
					f"{stringify(cls_names)} {status_msg(int(not is_equal))}"
				)
				assert is_equal
	test=TraversalTest()
	test.compare_implementations()
