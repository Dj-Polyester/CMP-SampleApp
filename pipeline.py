from typing import Callable, Union, Any, Iterable
from dataclasses import dataclass
import time, subprocess
from subprocess import CalledProcessError

def exists(obj: Any, attr: str):
	return hasattr(obj, attr) and getattr(obj, attr) != None
def tabbed_print(depth, *args, **kwargs):
	print("\t".expandtabs(4)*depth, *args, **kwargs)
@dataclass
class ExecutionException:
	runnable: 'Runnable'
	type: BaseException

class ExecutionResult:
	"""Result of pipeline execution."""
	def __init__(self, runnable: 'Runnable'):
		self.runnable = runnable
		self.elapsed_time: float = 0
		self.children: dict[Union[int, str], 'ExecutionResult'] = {}
	def completed(self):
		return not exists(self, "exception")
	def interrupted(self):
		return isinstance(self.exception.type, KeyboardInterrupt)
	def failed(self):
		return isinstance(self.exception.type, Exception)
	def __getitem__(self, key: Union[int, str]):
		return self.children[key]
	def __setitem__(self, key: Union[int, str], value: 'ExecutionResult'):
		self.children[key] = value
	def print(self, depth = 0):
		runnable_id = self.runnable.id
		title_txt = f"{self.runnable.type()} {runnable_id}"
		time_txt = f" time: {self.elapsed_time:.4f}"
		retval_txt = f" return: {self.return_value}" if exists(self, "return_value") else ""
		status_txt = f" {self.status_msg()}"
		exception_txt = None
		if not self.completed() and self.exception.runnable.id == runnable_id:
			exctype = self.exception.type
			exception_title_txt = type(exctype).__name__
			if hasattr(exctype, "stderr"):
				exception_explanatory_txt_tmp = exctype.stderr
			else:
				exception_explanatory_txt_tmp = str(exctype)

			exception_explanatory_txt = (
				f"[Errno {exctype.returncode}] " + exception_explanatory_txt_tmp
				if hasattr(exctype, "returncode")
				else exception_explanatory_txt_tmp
			)

			if exception_explanatory_txt_tmp != "":
				exception_explanatory_txt = ": " + exception_explanatory_txt

			exception_txt = f" ({exception_title_txt}{exception_explanatory_txt})"
		else:
			exception_txt = ""
		tabbed_print(
			depth,
			title_txt,":", time_txt, retval_txt, status_txt, exception_txt,
		)
		for child in self.children.values():
			child.print(depth+1)
	def status_msg(self) -> str:
		if self.completed():
			return "done ✓"
		elif self.interrupted():
			return "interrupted ⚠"
		elif self.failed():
			return "failed ✗"
		raise TypeError(f"Result has invalid exception type {type(self.exception)}")
class Runnable:
	REC_ATTRS = [
		"verbose"
	]
	def __init__(
		self,
		id: Union[int, str],
		verbose: bool = False,
	):
		self.id = id
		self.verbose = verbose
		self.depth = 0
	def _pipeline_setattr(self, name, val):
		raise NotImplementedError()
	def __setattr__(self, name, val):
		super().__setattr__(name, val)
		if name in Runnable.REC_ATTRS and isinstance(self, Pipeline):
			self._pipeline_setattr(name, val)
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
		self.result = ExecutionResult(self)
		try:
			self.run(*args, **kwargs)
		except BaseException as e:
			self.result.exception = ExecutionException(self, e)
		self.result.elapsed_time = time.perf_counter() - start
		if self.verbose:
			self.print(f"{self.type()} {self.id} {self.result.status_msg()}")
		if self.depth == 0:#is the root
			self.result.print()
		return self.result

class Task(Runnable):
	'''Runs a callable given to it'''
	def __init__(
		self,
		callable: Callable,
		*args,
		verbose=False,
		**kwargs,
	):
		super().__init__(callable.__name__, verbose)
		self.callable = callable
		self.args = args
		self.kwargs = kwargs
	def run(self, *_, **__):
		self.result.return_value = self.callable(*self.args, **self.kwargs)
	@staticmethod
	def shell(*args, **kwargs):
		result = subprocess.run(
            *args,
            **kwargs,
            check=True,  # This raises CalledProcessError on non-zero exit
            capture_output=True,  # Capture both stdout and stderr
            text=True,  # Return strings instead of bytes
        )
		result.check_returncode()
		return result

class Pipeline(Runnable):
	'''Runs its children runnables sequentially'''
	def __init__(
		self,
		id: Union[int, str],
		*children: Runnable,
		verbose=False,
	):
		self.children = children
		super().__init__(id, verbose)
	def _pipeline_setattr(self, name, val):
		for child in self.children:
			child.__setattr__(name, val)
	def run_child(self, child: Runnable) -> bool:
		child.depth = self.depth+1
		result = child()
		self.result.elapsed_time += result.elapsed_time
		self.result[child.id] = result
		if not result.completed():
			self.result.exception = result.exception
			return False
		return True
	def run(self):
		for child in self.children:
			if not self.run_child(child):
				break

class Multiplexer(Pipeline):
	'''Chooses number of its runnables given an indexing parameter. When the index is boolean, True becomes 0 and vice-versa'''
	def __init__(
		self,
		id: Union[int, str],
		index: Union[bool, int, Iterable[int]],
		*children: Union['Pipeline', Task],
		verbose=False,
	):
		super().__init__(id, *children, verbose = verbose)
		self.conditions = index
	def _precondition(self):
		if isinstance(self.conditions, bool):
			self.conditions = int(not self.conditions)
		if isinstance(self.conditions, int):
			self.conditions = [self.conditions]
	def run(self):
		self._precondition()
		for condition in self.conditions:
			if condition < len(self.children):
				if not self.run_child(self.children[condition]):
					break

if __name__ == "__main__":
	def demo_task_1():
		time.sleep(0.5)
		return True

	def demo_task_2():
		time.sleep(0.3)

	def demo_task_3():
		Task.shell(["ls", "afd"])

	def demo_task_4():
		time.sleep(0.7)
	def test1():
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
	def test2():
		print("Running test2")
		Multiplexer(3,
			[2,3,0],
			Pipeline(4,
				Task(demo_task_1),
			),
			Pipeline(5,
				Task(demo_task_2),
				Task(demo_task_3),
			),
			Pipeline(4,
				Task(demo_task_4),
			),
			verbose=True,
		)()
	def test3():
		print("Running test3")
		Multiplexer(3,
			True,
			Pipeline(4,
				Task(demo_task_1),
			),
		)()
	def test4():
		print("Running test4")
		Multiplexer(3,
			False,
			Pipeline(4,
				Task(demo_task_1),
			),
	)()
	test2()
	test3()
	test4()
