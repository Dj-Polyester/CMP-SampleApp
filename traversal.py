from typing import Any, Callable, Optional, Union
from collections import deque
from log import log
from utils import (
	Result,
	Attrs,
	stringify,
	stringify_map,
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
	}
	VALID_PARAMS = {
		"pop": Param(str),
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
		"proc_children": Param(Callable),
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
		"proc_children": Param(Callable, lambda x: x),
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
		).set_check(
			self.config,
			self,
			_return = False,
		)
	def __call__(self, items= Param.DEFAULT):
		container = TraversalContainer(self.config)
		container._setup(items)
		return container
	def empty(self):
		return not self._container
	def __getitem__(self, index: int):
		return self._container[index] if self._container else Param.DEFAULT
	def top(self):
		return self[self.config.top_index]
	def bottom(self):
		ti = self.config.top_index
		if ti == 0:
			ti = -1
		elif ti == -1:
			ti = 0
		else:
			raise InvalidVal("top_index", ti, (0,-1))
		return self[ti]
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
	def print(self):
		log.print(self, _level = log.DEBUG)
	def get_containers(self, *params):
		_valid_keys = TraversalTypeConfig.keys("valid")
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
		_values = [
			container_cls[i](p) for i, p in enumerate(params)
		] + [
			c() for c in container_cls[len(params):]
		]
		return dict(zip(_valid_keys, _values))
	def _config_containers(self, **containers):
		for name, container in containers.items():
			container.name = name
			container.reverse = not container.is_stack and "parent" in name
	def set_containers(
		self,
		*params,
		**containers: TraversalContainer,
	):
		if params != [] and containers != {}:
			raise ValueError("Both params and containers are nonempty")
		elif containers == {}:
			containers = self.get_containers(*params)
		else:
			containers = {**self.get_containers(), **containers}
		self._config_containers(**containers)
		_valid_keys = TraversalTypeConfig.keys("valid")
		Attrs(_valid_keys).set_check(
			containers,
			self,
			_return = False,
		)
		self.containers = containers
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
	def run(self, func_name: str, container_name_parent: str):
		parent_node = self._container(container_name_parent).top()
		callback_ret = self._callback(func_name)(
			parent_node,
			self.node,
		)
		if isinstance(callback_ret, Result):
			self.result = callback_ret
		else:
			self.result = Result()
			self.result.set_code(callback_ret)
		return self.result
	def add_children(self):
		if self.type_config.special_token_before_children:
			self.container.add_single(self.config.special_token)
		if Attrs.has(self.node, "children"):
			children = self.node.children
			if isinstance(children, dict):
				children = children.values()

			if (
				Attrs.has(self.node, "proc_children") and
				isinstance(self.node.proc_children, Callable)
			):
				children = self.node.proc_children(children)
			self.container.add_multiple(
				self.type_config.proc_children(children)
			)
		if not self.type_config.special_token_before_children:
			self.container.add_single(self.config.special_token)
	def set_env_vars(self, **env_vars):
		Attrs().set_check(
			env_vars,
			self.node,
			_return = False,
		)
		self.env_vars = env_vars
	def forward(self, **env_vars):
		self.node = self.container.pop()
		if self.node == self.config.special_token: # Processed all children
			self.node = self.parent_container.pop()
			self.run("node_finalize", "parent_container")
		else:
			self.set_env_vars(**env_vars)
			self.add_children()
			self.run("node_init", "parent_container")
			if self.result.none():
				self.parent_container.add_single(self.node)
				self.backtrack_container.add_single(self.node)
	def backward_container(self, container_name: str):
		self.run("node_backward", container_name)
		self.node = self._container(container_name).pop()
	def backward_parent(self):
		self.config.node_backward(self.node.parent, self.node)
		self.node = self.node.parent
	def __repr__(self):
		_props = self.props(self.type_config, "valid")
		_other_props = ["result", "node"]
		for prop in _other_props:
			if Attrs.has(self, prop):
				_props[prop] = getattr(self, prop)
		return log.repr(f"TraverseState({stringify_map(_props)})")
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
			condition_name = lambda x: Attrs.has(state_config, x),
		)
		_valid_props = attrs.get(state_config)
		_self_props = attrs._with(
			_valid_defaults.keys(),
			condition_name = lambda x: Attrs.has(self, x),
			condition_val = lambda x: x != Param.DEFAULT,
		).get(self)
		_all_valid = {**_valid_defaults, **_valid_props, **_self_props}
		attrs._with(
			TraversalStateConfig.keys("valid")
		).set_check(
			_all_valid,
			state_config,
			_return = False,
		)
	def __getattr__(self, name: str):
		if name in self.PRECONFIGS:
			def _recursive(
				state_config: TraversalStateConfig,
				obj: Optional[Any] = Param.DEFAULT,
				**env_vars,
			):
				return self.recursive(
					state_config=state_config,
					type_config=name,
					obj=obj,
					**env_vars,
				)
			return _recursive
		elif Attrs.has(self, "state"):
			return getattr(self.state, name)
		else:
			raise InvalidAttr(self, name)
	def recursive(
		self,
		state_config: TraversalStateConfig,
		type_config: Union[str, TraversalTypeConfig],
		obj: Optional[Any] = Param.DEFAULT,
		**env_vars,
	):
		self.setup(state_config, type_config)
		if obj == Param.DEFAULT:
			obj = self

		self.set_containers([obj])
		self.print()
		while not self.container.empty():
			self.forward(**env_vars)
			self.print()
			if self.result.exists():
				break
		return self.result
	def recursive_backward(self, backward_mode = Param.DEFAULT):
		if backward_mode != Param.DEFAULT:
			self.state.config.backward_mode = backward_mode
		self.print()
		is_container, bm_container_name = self.state.config.backward_container()
		if is_container:
			while not getattr(self.state, bm_container_name).empty():
				self.backward_container(bm_container_name)
				self.print()
		elif self.state.config.backward_mode == "parent_pointer":
			while Attrs.has(self.state.node, "parent"):
				self.backward_parent()
				self.print()
		if is_container or self.state.config.backward_mode == "parent_pointer":
			self.config.node_backward(Param.DEFAULT, self.node)
			self.print()
		else:
			raise InvalidVal(
				"Backward mode",
				self.state.config.backward_mode,
				tuple(TraversalStateConfig.VALID_BACKWARD_MODES.keys()),
			)

if __name__ == "__main__":
	def _print_condition(obj: Any, *args, **kwargs):
		if Attrs.getitem(obj,"holder_type") != "IDummy" or Attrs.getitem(obj,"proc_other"):
			print(*args, **kwargs)
	def callbacktxt(prefix, parent, obj):
		parent_id = "" if parent == Param.DEFAULT else parent.id
		_callbacktxt = f"{prefix} {parent_id} {obj.id}"
		Dummy.buffertxt.append(_callbacktxt)
		_print_condition(obj, _callbacktxt)
	def node_init(*args):
		callbacktxt("node_init", *args)
		if args[1].id == 6:
			return False
	def node_finalize(*args):
		callbacktxt("node_finalize", *args)
	def node_backward(*args):
		callbacktxt("node_backward", *args)

	class Dummy(Traversal):
		buffertxt: list
		def __init__(self, id, *children):
			Dummy.buffertxt = []
			self.id = id
			self.set_children(children)
		def set_children(self, children):
			self.children = children
			for child in self.children:
				child.parent = self
		def __repr__(self):
			return repr(self.id)
		def backward(self, res: Result, **env_vars):
			_print_condition(env_vars, "Backward:")
			if res.exists():
				self.recursive_backward()
		def __call__(self, **env_vars):
			_print_condition(
				env_vars, f"Class {Attrs.getitem(env_vars, "holder_type")}:\nForward:"
			)

	class UDummy(Dummy):
		def __call__(
			self,
			_type,
			backward_mode: str,
			**env_vars,
		):
			super().__call__(**env_vars)
			res = getattr(self, _type)(
				state_config = TraversalStateConfig(
					node_init = node_init,
					node_finalize = node_finalize,
					node_backward = node_backward,
					backward_mode = backward_mode,
				),
				**env_vars,
			)
			self.backward(res, **env_vars)

	class IDummy(Dummy):
		@staticmethod
		def node_init(*args):
			return node_init(*args)
		@staticmethod
		def node_finalize(*args):
			return node_finalize(*args)
		@staticmethod
		def node_backward(*args):
			return node_backward(*args)
		def __call__(
			self,
			_type,
			backward_mode: str,
			**env_vars,
		):
			super().__call__(**env_vars)
			res = getattr(self, _type)(
				state_config = TraversalStateConfig(
					backward_mode = backward_mode,
				),
				**env_vars,
			)
			self.backward(res, **env_vars)

	class TraversalTest(Test):
		@staticmethod
		def _sample(cls_type: type):
			return cls_type(
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
			)
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
			_assert = False
			params = {
				"_type": TraversalState.PRECONFIGS.keys(),
				"backward_mode": TraversalStateConfig.VALID_BACKWARD_MODES.keys(),
			}
			cls_types = [
				UDummy,
				IDummy,
			]
			env_vars = dict(
				proc_other = False,
			)
			cls_names = [t.__name__ for t in cls_types]
			def _callback_inner(cls_type, param):
				env_vars["holder_type"] = cls_type.__name__
				TraversalTest._sample(cls_type)(
					**param,
					**env_vars,
				)
				return Dummy.buffertxt
			def _callback_outer(buffer_txts):
				is_equal = buffer_txts[0] == buffer_txts[1]
				print(
					f"{stringify(cls_names)} {Result(int(not is_equal)).status_msg()}"
				)
				if _assert:
					assert is_equal
			self._compare_classes(
				cls_types,
				params,
				_callback_inner,
				_callback_outer,
			)
	#log.setLevel(log.DEBUG)
	test=TraversalTest()
	test.compare_implementations()
