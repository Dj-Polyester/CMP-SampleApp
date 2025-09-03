from typing import Any, Callable, Optional, Iterable
from collections import deque
from utils import exists, setattrs
from dataclasses import dataclass, field

@dataclass
class TraverseContainerArgs:
	_type: type = list
	top_index: Optional[int] = -1
	pop_func: Optional[str] = "pop"
	add_func: Optional[str] = "append"
	add_multiple_func: Optional[Callable] = None

class TraverseContainer:
	PRECONFIGS = {
		"bfs": TraverseContainerArgs(deque, 0, "popleft"),
		"dfs": TraverseContainerArgs(),
	}
	def __init__(
		self,
		traverse_type: Optional[str] = None,
		args: Optional[TraverseContainerArgs] = None,
	):
		if traverse_type != None:
			self.args = TraverseContainer.PRECONFIGS[traverse_type]
		elif args != None:
			self.args = args
		else:
			raise ValueError("Either traverse type or arguments must be provided")
	def __call__(self, args=None):
		self._container = self.args._type() if args == None else self.args._type(args)
		self.pop = getattr(self._container, self.args.pop_func)
		self.add = getattr(self._container, self.args.add_func)
		self.add_multiple = getattr(self._container, self.args.add_multiple_func)
		return self
	def top(self):
		return self._container[self.args.top_index] if self._container else None

class Traverse:
	def __init__(self, _type: Optional[str] = None):
		self.type = _type
		self.containercls = TraverseContainer(_type)

	def recurse(
		self,
		obj: Any,
		callback: Callable = lambda _,__: _,
		after: Callable = lambda _, __: _,
		cleanup: Callable = lambda _, __: _,
		_type: str = "bfs",
	):
		container = self.containercls([obj])
		parent_container = self.containercls()
		def _neg(res):
			return isinstance(res, bool) and not res
		success = False
		node = None
		while container:
			node = container.pop()
			if node == None: # Processed all children
				node = parent_container.pop()
				success = after(parent_container.top(), node)
			else:
				if _type == "dfs":
					container.add(None)
				if exists(node, "children"):
					children = node.children.values() if isinstance(node.children, dict) else node.children
					container.extend(arg.proc_func(children))
				if _type == "bfs":
					container.append(None)
				parent_node = get_parent()
				parent_container.append(node)
				success = callback(parent_node, node)
			if _neg(success):
				break
		while parent_container:
			cleanup(get_parent(), node)
			node = getattr(parent_container, arg.pop)()

def bfs(
	obj: Any,
	callback: Callable = lambda _,__: _,
	after: Callable = lambda _, __: _,
	cleanup: Callable = lambda _, __: _,
):
	search(
		obj,
		callback,
		after,
		cleanup,
		"bfs"
	)
def dfs(
	obj: Any,
	callback: Callable = lambda _,__: _,
	after: Callable = lambda _, __: _,
	cleanup: Callable = lambda _, __: _,
):
	search(
		obj,
		callback,
		after,
		cleanup,
		"dfs"
	)

if __name__ == "__main__":
	class Dummy:
		def __init__(self, id, *children):
			self.id = id
			self.children = children
	def before(obj):
		print(f"before obj {obj.id}")
	def after(obj):
		print(f"after obj {obj.id}")

	d = Dummy(
		1,
		Dummy(
			2,
			Dummy(
				4
			),
			Dummy(
				5
			),
		),
		Dummy(
			3,
			Dummy(
				6
			),
			Dummy(
				7
			),
		),
	)
	print("dfs")
	dfs(
		d,
		before,
		after,
	)
	print("\nbfs")
	bfs(
		d,
		before,
		after,
	)
