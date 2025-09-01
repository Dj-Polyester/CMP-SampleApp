from typing import Any, Callable
from collections import deque
from dataclasses import dataclass, Field
from utils import exists

@dataclass
class SearchArgs:
	container_type: str
	pop: str
	top: int
	proc_func: Callable

def search(
	obj: Any,
	callback: Callable = lambda _,__: _,
	after: Callable = lambda _, __: _,
	cleanup: Callable = lambda _, __: _,
	_type: str = "bfs",
):
	valid_args = {
		"bfs": SearchArgs("deque","popleft", 0, lambda c: c),
		"dfs": SearchArgs("list","pop", -1, lambda c: reversed(c)),
	}
	if _type not in valid_args:
		raise ValueError(f"Search has the wrong type {_type}")
	arg = valid_args[_type]

	container = eval(arg.container_type)([obj])
	parent_container = eval(arg.container_type)()
	def get_parent():
		return parent_container[arg.top] if parent_container else None
	def _true(res):
		return isinstance(res, bool) and res
	failed = False
	node = None
	while container:
		node = getattr(container, arg.pop)()
		if node == None: # Processed all children
			node = getattr(parent_container, arg.pop)()
			failed = after(get_parent(), node)
		else:
			if _type == "dfs":
				container.append(None)
			if exists(node, "children"):
				children = node.children.values() if isinstance(node.children, dict) else node.children
				container.extend(arg.proc_func(children))
			if _type == "bfs":
				container.append(None)
			parent_node = get_parent()
			parent_container.append(node)
			failed = callback(parent_node, node)
		if _true(failed):
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
