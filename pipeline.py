from typing import Callable, Union, Any, Optional
from dataclasses import dataclass, field
import time
import subprocess

def exists(obj: Any, attr: str):
	return hasattr(obj, attr) and getattr(obj, attr) != None
def tabbed_print(depth, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
@dataclass
class ExecutionException:
	id: Union[int, str]
	type: BaseException
@dataclass
class ExecutionResult:
	"""Result of pipeline execution."""
	id: Union[int, str]
	return_value: Optional[Any] = None
	elapsed_time: float = 0.0
	exception: Optional[ExecutionException] = None
	children: dict[Union[int, str], 'ExecutionResult'] = field(default_factory=dict)
	def completed(self):
		return self.exception == None
	def interrupted(self):
		return isinstance(self.exception, KeyboardInterrupt)
	def failed(self):
		return isinstance(self.exception, Exception)
	def __getitem__(self, key: Union[int, str]):
		return self.children[key]
	def __setitem__(self, key: Union[int, str], value: 'ExecutionResult'):
		self.children[key] = value
	def print(self, depth = 0):
		e = f"exception: {repr(self.exception.type)}" if exists(self, "exception") and self.exception.id == self.id else ""
		tabbed_print(
			depth ,f"Task {self.id}: time: {self.elapsed_time:.4f} {e} return: {self.return_value}"
		)
		for child in self.children.values():
			child.print(depth+1)

class Runnable:
	def __init__(
		self,
		id: Union[int, str],
		verbose: bool = True,
	):
		self.id = id
		self.verbose = verbose
		self.depth = 0
	def print(self, *args, **kwargs):
		if self.verbose:
			tabbed_print(self.depth, *args, **kwargs)
	def run(self):
		raise NotImplementedError()
	def type(self) -> str:
		return type(self).__name__
	def setdepth(self):
		if not exists(self, "depth"):
			self.depth = 0
	def __call__(self, *args, **kwargs) -> ExecutionResult:
		self.setdepth()
		self.print(f"{self.type()} {self.id} started")
		start = time.perf_counter()
		self.result = ExecutionResult(self.id)
		try:
			self.run(*args, **kwargs)
		except BaseException as e:
			self.result.exception = ExecutionException(self.id, e)
			if self.verbose:
				if self.result.interrupted():
					self.print(f"{self.type()} {self.id} interrupted ⚠")
				elif self.result.failed():
					self.print(f"{self.type()} {self.id} failed ✗")
		self.result.elapsed_time = time.perf_counter() - start
		self.print(f"{self.type()} {self.id} done ✓")
		if self.depth == 0:#is the root
			self.result.print()
		return self.result

class Task(Runnable):
	def __init__(
		self,
		callable: Callable,
		*args,
		**kwargs
	):
		super().__init__(callable.__name__)
		self.callable = callable
		self.args = args
		self.kwargs = kwargs
	def run(self, *_, **__):
		self.result.return_value = self.callable(*self.args, **self.kwargs)

class Pipeline(Runnable):
	def __init__(
		self,
		id: Union[int, str],
		*children: Union['Pipeline', Task],
	):
		super().__init__(id)
		self.children = children
	def run(self):
		for child in self.children:
			child.depth = self.depth+1
			result = child()
			self.result.elapsed_time += result.elapsed_time
			self.result[child.id] = result
			if not result.completed():
				self.result.exception = result.exception
				break


def demo_task_1():
	time.sleep(0.5)
	return True

def demo_task_2():
	time.sleep(0.3)
	return True

def demo_task_3():
	subprocess.run(["ls", "afd"])
	return True

def demo_task_4():
	time.sleep(0.7)
	return True
Pipeline(1,
	Pipeline(2,
		Task(demo_task_1),
		Task(demo_task_2),
	),
	Task(demo_task_3),
	Task(demo_task_4),
)()
Pipeline(3,
	Pipeline(4,
		Task(demo_task_1),
	),
	Pipeline(5,
		Task(demo_task_2),
		Task(demo_task_3),
	),
)()
