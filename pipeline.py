from typing import Callable, Union, Iterable, Optional
from dataclasses import dataclass
import time, subprocess, reprlib, inspect, multiprocessing as mp
from search import bfs, dfs
from utils import exists, tabbed_print

@dataclass
class ExecutionException:
	runnable: 'Runnable'
	type: BaseException

class ExecutionResult:
	"""Result of pipeline execution."""
	def __init__(self, runnable: 'Runnable'):
		self.runnable = runnable
		self.elapsed_time: float = 0
		self.children:  dict[Union[int, str], 'ExecutionResult'] = {}
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
	@staticmethod
	def tabbed_print(obj: 'ExecutionResult'):
		runnable_id = obj.runnable.id
		title_txt = f"{obj.runnable.type()} {runnable_id}"
		time_txt = f" time: {obj.elapsed_time:.4f}"
		if exists(obj, "return_value"):
			retval_repr = obj.return_value if obj.runnable.verbose else reprlib.repr(obj.return_value)
			retval_txt = f" return: {retval_repr}"
		else:
			retval_txt = ""
		status_txt = f" {obj.status_msg()}"
		exception_txt = None
		if not obj.completed() and obj.exception.runnable.id == runnable_id:
			exctype = obj.exception.type
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
			obj.depth,
			title_txt,":", time_txt, retval_txt, status_txt, exception_txt,
		)
	def print(self):
		bfs(self, ExecutionResult.tabbed_print)
	def status_msg(self) -> str:
		if self.completed():
			return "done ✓"
		elif self.interrupted():
			return "interrupted ⚠"
		elif self.failed():
			return "failed ✗"
		raise TypeError(f"Result has invalid exception type {type(self.exception)}")
class Runnable:
	def __init__(
		self,
		id: Optional[Union[int, str]] = None,
		verbose:bool = False,
	):
		self._setattrs(
			id=id,
			depth=0,
			verbose=verbose,
		)
	def _setattrs(self, **attrs):
		for name, val in attrs.items():
			setattr(self, name, val)

	def _get_parent_runnable(self) -> tuple[Optional['Runnable'], Optional['Runnable']]:
		def isrunnable(frame):
			return "self" in frame.f_locals and isinstance(frame.f_locals["self"], Runnable)
		def is_global_scope(frame):
			return "__name__" in frame.f_locals and frame.f_locals["__name__"] == "__main__"
		frame = inspect.currentframe()
		if frame == None:
			raise TypeError("Cannot find the current frame frame is None")
		# Look for the first non-runnable to go outer boundaries of the current runnable
		while True:
			frame = frame.f_back
			if not isrunnable(frame):
				break
		# Look for the first runnable if not in global scope yet
		runnable = None
		multitask_runnable = None
		while True:
			if is_global_scope(frame):
				break
			frame = frame.f_back
			if isrunnable(frame):
				runnable = frame.f_locals["self"]
				if isinstance(runnable, Pipeline):
					multitask_runnable = runnable
				break
		if runnable != None and multitask_runnable == None:# couldnt find a pipeline runnable and still not global
			while True:
				if is_global_scope(frame):
					break
				frame = frame.f_back
				if isrunnable(frame) and isinstance(runnable, MultiTask):
					multitask_runnable = frame.f_locals["self"]
					break
		return runnable, multitask_runnable
	def print(self, *args, **kwargs):
		if self.verbose:
			tabbed_print(self.depth, *args, **kwargs)
	def run(self):
		raise NotImplementedError()
	def _run_single(self):
		pass
	def type(self) -> str:
		return type(self).__name__
	def __call__(self):
		return self.run()
	@staticmethod
	def _set_id_attrs(parent: Optional['Runnable'], obj: 'Runnable'):
		if obj.id == None:
			obj.id = MultiTask.next_id
			MultiTask.next_id+=1
		if parent != None:
			for name in MultiTask.REC_ATTRS:
				setattr(obj, name, getattr(parent, name))
	@staticmethod
	def _init(parent: Optional['Runnable'], obj: 'Runnable'):
		Runnable._set_id_attrs(parent, obj)
		obj.print(f"{obj.type()} {obj.id} started")
		obj.result = ExecutionResult(obj)
		obj.result.depth = obj.depth
		obj.start = time.perf_counter()
	@staticmethod
	def _final(parent: Optional['Runnable'], obj: 'Runnable') -> bool:
		obj._run_single()
		elapsed_time = time.perf_counter() - obj.start
		obj.result.elapsed_time = elapsed_time
		obj.print(f"{obj.type()} {obj.id} {obj.result.status_msg()} {elapsed_time:.4f}")

		if parent != None:
			parent.result[obj.id] = obj.result
		return obj.result.completed()
	@staticmethod
	def _cleanup(parent: Optional['Runnable'], obj: 'Runnable'):
		if parent != None:
			parent.result[obj.id] = obj.result
			parent.result.exception = obj.result.exception


class Task(Runnable):
	'''Runs a callable given to it'''
	def __init__(
		self,
		cmd: Union[Callable, list, str],
		*args,
		verbose=False,
		id: Optional[Union[int,str]]=None,
		**kwargs,
	):
		if id == None:
			if isinstance(cmd, Callable):
				id = cmd.__name__
				self.callable = cmd
				self.args = args
			elif isinstance(cmd, str):
				id = f'"{cmd}"'
				self.set_shell()
				self.args = [cmd.split()] + list(args)
			elif isinstance(cmd, list):
				id = f'"{" ".join(cmd)}"'
				self.set_shell()
				self.args = [cmd] + list(args)
			else:
				raise TypeError(f"Command has wrong type {type(cmd)}")
		self.kwargs = kwargs
		super().__init__(id, verbose)
	def set_shell(self):
		self.callable = self.shell_capture
	def is_shell(self):
		return self.callable == self.shell_capture
	def _run_single(self):
		return self.run()
	def run(self):
		if self.is_shell():
			self.print_process = mp.Process(
				target=Task.shell_print,
				args=self.args,
				kwargs=self.kwargs
			)
			self.print_process.start()
		try:
			self.result.return_value = self.callable(*self.args, **self.kwargs)
		except BaseException as e:
			self.result.exception = ExecutionException(self, e)
		if self.is_shell():
			self.print_process.join()

	@staticmethod
	def shell_capture(*args, **kwargs):
		'''Capture output but don't print'''
		return subprocess.run(
			*args,
			**kwargs,
			check=True,  # This raises CalledProcessError on non-zero exit
			capture_output=True,  # Capture both stdout and stderr
			text=True,  # Return strings instead of bytes
		)
	@staticmethod
	def shell_print(*args, **kwargs):
		'''Print but don't capture output'''
		return subprocess.run(*args, **kwargs)

class MultiTask(Runnable):
	next_id = 1
	REC_ATTRS = [
		"verbose",
	]
	'''Runnable with multiple runnables'''
	def __init__(
		self,
		*children: Runnable,
		id: Optional[Union[int, str]] = None,
		verbose=False,
	):
		super().__init__(id, verbose)
		self._set_tree_onedepth(children)
	def _set_tree_onedepth(self, children):
		self.children = children
		for child in self.children:
			child.parent = self
			child.depth += 1
class Pipeline(MultiTask):
	'''Runs its children runnables sequentially'''
	def __init__(
		self,
		*children: Runnable,
		id: Optional[Union[int, str]] = None,
		verbose=False,
	):
		super().__init__(*children, id=id, verbose=verbose)
	def run(self):
		return dfs(
			self,
			Runnable._init,
			Runnable._final,
			Runnable._cleanup,
		)

class Multiplexer(Pipeline):
	'''Chooses number of its runnables given an indexing parameter. When the index is boolean, True becomes 0 and vice-versa'''
	def __init__(
		self,
		index: Union[bool, int, Iterable[int]],
		*children: Union['Pipeline', Task],
		id: Optional[Union[int, str]] = None,
		verbose=False,
	):
		super().__init__(*children, id=id, verbose=verbose)
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

	demo_task_3 = Task(["ls", "composeApp"])

	def demo_task_4():
		time.sleep(0.7)

	demo_task_5 = Task(["ls", "afd"])
	demo_task_6 = Task(["./gradlew", ":composeApp:assembleDebug"])

	def test1():
		print("Running test1")
		Pipeline(
			Pipeline(
				Task(demo_task_1),
				Task(demo_task_2),
			),
			demo_task_3,
			Task(demo_task_4),
			verbose=True,
		)()
		Pipeline(
			Pipeline(
				Task(demo_task_1),
			),
			Pipeline(
				Task(demo_task_2),
				demo_task_3,
			),
			verbose=True,
		)()
	def test2():
		print("Running test2")
		Pipeline(
			Pipeline(
				Pipeline(
					Task(demo_task_1),
				),
				Pipeline(
					Task(demo_task_2),
					demo_task_3,
				),
				id="a",
			),
			demo_task_3,
			Pipeline(
				Task(demo_task_1),
			),
			Pipeline(
				Task(demo_task_2),
				Pipeline(
					Task(demo_task_1),
				),
				Pipeline(
					Task(demo_task_2),
					demo_task_3,
					id="b",
				),
			),
			Task(demo_task_4),
			verbose=True,
		)()
	def test3():
		print("Running test3")
		Multiplexer(
			[2,3,0],
			Pipeline(
				Task(demo_task_1),
			),
			Pipeline(
				Task(demo_task_2),
				demo_task_5,
			),
			Pipeline(
				Task(demo_task_4),
			),
			verbose=True,
		)()
		Multiplexer(
			True,
			Pipeline(
				Task(demo_task_1),
			),
		)()
		Multiplexer(
			False,
			Pipeline(
				Task(demo_task_1),
			),
		)()

	def test4():
		print("Running test4")
		def subfunc():
			Pipeline(
				demo_task_3,
				Task(demo_task_4),
			)()
		Pipeline(
			Pipeline(
				Task(demo_task_1),
				Task(demo_task_2),
			),
			Task(subfunc),
			verbose=True,
		)()
		Pipeline(
			Pipeline(
				Task(demo_task_1),
				Task(demo_task_2),
				id="b",
			),
			Task(subfunc),
			verbose=True,
			id="a"
		)()
	test1()
