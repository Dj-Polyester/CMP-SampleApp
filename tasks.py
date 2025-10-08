from pathlib import Path
import time, subprocess, inspect, multiprocessing as mp
from typing import Callable, Union, Iterable, Optional, Sequence
from dataclasses import dataclass
from traversal import Traversal, TraversalStateConfig
from utils import InvalidType, InvalidVal, Param, Result, repr_from_map, repr_from_maps, stringify_map, tabbed_print, Attrs
from test import Test
from log import log

@dataclass
class ExecutionException:
	runnable: 'Runnable'
	type: BaseException

@dataclass
class ExecutionResult(Result, Traversal):
	"""Result of pipeline execution."""
	def __init__(self, runnable: 'Runnable'):
		self.runnable = runnable
		self.elapsed_time: float = 0
		self.children:  dict[Union[int, str], 'ExecutionResult'] = {}
	def __repr__(self):
		_map = {
			"runnable": self.runnable,
			"elapsed_time": self.elapsed_time,
		}
		_seq = [
			"exception",
			"return_value",
		]
		return repr_from_maps(self, _map, _seq)
	def break_condition(self):
		return self.failed() or self.interrupted()
	def __getitem__(self, key: Union[int, str]):
		return self.children[key]
	def __setitem__(self, key: Union[int, str], value: 'ExecutionResult'):
		self.children[key] = value
	@staticmethod
	def _tabbed_print(_, obj: 'ExecutionResult'):
		runnable_id = obj.runnable.id
		title_txt = f"{obj.runnable.type()} {runnable_id}"
		time_txt = f" time: {obj.elapsed_time:.4f}"
		if Attrs.has(obj, "return_value"):
			retval_repr = log.repr(obj.return_value)
			retval_txt = f" return: {retval_repr}"
		else:
			retval_txt = ""
		status_txt = f" {obj.status_msg()}"
		exception_txt = None
		if obj.break_condition() and obj.exception.runnable.id == runnable_id:
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
	def print(
		self,
		traversal_type = "dfs",
		backward_mode = "parent",
	):
		print("\nResults:")
		getattr(self, traversal_type)(
			state_config = TraversalStateConfig(
				backward_mode = backward_mode,
				node_init = ExecutionResult._tabbed_print,
			)
		)
class Runnable(Traversal):
	current_instances: dict[Union[int, str], 'Runnable'] = {}
	def __init__(
		self,
		id: Optional[Union[int, str]] = None,
	):
		Attrs().set({
				"id":id,
				"depth": 0,
			},
			self,
		)
	def __del__(self):
		del Runnable.current_instances[self.id]
	def __repr__(self):
		_map = {
			"id":self.id,
			"depth":self.depth,
		}
		return repr_from_map(self, _map)
	def print(self, *args, **kwargs):
		if log.verbose():
			tabbed_print(self.depth, *args, **kwargs)
	def run(self) -> ExecutionResult:
		raise NotImplementedError()
	def _run_single(self) -> ExecutionResult:
		self.result.set_code(0)
		return self.result
	def _get_parent_runnable_call_stack(self, _ret_multitask = False) -> Optional['Runnable']:
		def is_runnable_frame(frame, _type = Runnable):
			return "self" in frame.f_locals and isinstance(frame.f_locals["self"], _type)
		def is_runnable(obj, _type = Runnable):
			return isinstance(obj, _type)
		def is_global(frame):
			return frame.f_locals == frame.f_globals
		frame = inspect.currentframe()
		if frame == None:
			raise ValueError("Frame is None")
		runnable: Optional[Task] = None
		while not is_global(frame):
			if is_runnable_frame(frame, Task):
				runnable = frame.f_locals["self"]
				break
			frame = frame.f_back
		if runnable != None: # Found a task
			if not _ret_multitask:
				return runnable
			while Attrs.has(runnable, "parent") and not is_runnable(runnable, MultiTask):
				runnable = runnable.parent
			if is_runnable(runnable, MultiTask):
				return runnable

	def _call_setup(self, *args, **kwargs):
		if not Attrs.has(self, "parent"):
			parent_runnable = self._get_parent_runnable_call_stack(*args, **kwargs)
			if parent_runnable != None:
				if not Attrs.has(parent_runnable, "children"):
					parent_runnable.children = []
				if self not in parent_runnable.children:
					parent_runnable.children.append(self)
				Runnable._set_id_depth_parent_attrs(parent_runnable, self)
	def __call__(self, *args, **kwargs):
		self._call_setup(*args, **kwargs)
		self.run(*args, **kwargs)
		if self.depth == 0:
			self.result.print()
		return self.result
	def _set_auto_id(self):
		raise NotImplementedError()
	@staticmethod
	def _set_id_depth_parent_attrs(parent: Optional['Runnable'], obj: 'Runnable'):
		obj._set_auto_id()
		if parent != None:
			obj.depth = parent.depth + 1
			obj.parent = parent
			Attrs(MultiTask.REC_ATTRS).set(parent, obj)
	def save(self):
		Runnable.current_instances[self.id] = self
	@staticmethod
	def _node_init_setup(parent: Optional['Runnable'], obj: 'Runnable'):
		Runnable._set_id_depth_parent_attrs(parent, obj)
		obj.save()
	def get_result(self):
		return ExecutionResult(self)
	@staticmethod
	def node_init(parent: Optional['Runnable'], obj: 'Runnable'):
		Runnable._node_init_setup(parent, obj)
		obj.print(f"{obj.type()} {obj.id} started")
		obj.result = obj.get_result()
		obj.result.depth = obj.depth
		obj.start = time.perf_counter()
		obj._run_single()
		return obj.result
	@staticmethod
	def node_finalize(parent: Optional['Runnable'], obj: 'Runnable'):
		elapsed_time = time.perf_counter() - obj.start
		obj.result.elapsed_time = elapsed_time
		if parent != None:
			parent.result.code = obj.result.code
			parent.result[obj.id] = obj.result
			parent.result.elapsed_time += elapsed_time
		obj.print(f"{obj.type()} {obj.id} {obj.result.status_msg()} {elapsed_time:.4f}")
	@staticmethod
	def node_backward(parent: Optional['Runnable'], obj: 'Runnable'):
		if parent != None:
			parent.result[obj.id] = obj.result
			parent.result.exception = obj.result.exception


class Task(Runnable):
	'''Runs a callable given to it'''
	def __init__(
		self,
		cmd: Union[Callable, list, str],
		*args,
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
				self.args = [str(cmd).split()] + list(args)
			elif isinstance(cmd, list):
				id = f'"{" ".join(cmd)}"'
				self.set_shell()
				self.args = [cmd] + list(args)
			else:
				raise TypeError(f"Command has wrong type {type(cmd)}")
		self.kwargs = kwargs
		super().__init__(id)
	def _set_auto_id(self):
		pass
	def set_shell(self):
		self.callable = self.shell_capture
	def is_shell(self):
		return self.callable == self.shell_capture
	def _run_single(self) -> ExecutionResult:
		return self.run()
	def run(self) -> ExecutionResult:
		"""
		if self.is_shell():
			self.print_process = mp.Process(
				target=Task.shell_print,
				args=self.args,
				kwargs=self.kwargs
			)
			self.print_process.start()
		"""
		try:
			self.result.return_value = self.callable(*self.args, **self.kwargs)
		except BaseException as e:
			self.result.set_code(e)
			self.result.exception = ExecutionException(self, e)
		else:
			self.result.set_code(0)
		"""
		if self.is_shell():
			self.print_process.join()
		"""
		return self.result

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
	'''Runnable with multiple runnables'''
	next_id = 1
	REC_ATTRS = []
	def __init__(
		self,
		*children: Runnable,
		id: Optional[Union[int, str]] = None,
	):
		super().__init__(id)
		self.children = list(children)
	def _set_auto_id(self):
		if self.id == None:
			self.id = MultiTask.next_id
			MultiTask.next_id+=1
	def run(
		self,
		traversal_type: str = "dfs",
		backward_mode: str = "parent",
		parent_pointer: bool = True,
	) -> ExecutionResult:
		result = getattr(self, traversal_type)(
			TraversalStateConfig(
				backward_mode = backward_mode,
				parent_pointer = parent_pointer,
			),
		)
		if result.break_condition():
			self.recursive_backward()
		return result
class Pipeline(MultiTask):
	'''Runs its children runnables sequentially'''
	def __init__(
		self,
		*children: Runnable,
		id: Optional[Union[int, str]] = None,
	):
		super().__init__(*children, id=id)

class Multiplexer(Pipeline):
	"""
	Chooses number of its runnables given an indexing parameter.
	When the index is boolean, True becomes 0 and vice-versa
	"""
	def __init__(
		self,
		index: Union[bool, int, Iterable[int]],
		*children: Union['Pipeline', Task],
		id: Optional[Union[int, str]] = None,
	):
		super().__init__(*children, id=id)
		self.set_conditions(index)
	def set_conditions(self, index):
		if isinstance(index, bool):
			self.conditions = [int(not index)]
		elif isinstance(index, int):
			self.conditions = [index]
		elif isinstance(index, Iterable):
			self.conditions = index
		else:
			raise InvalidType(
				"index",
				index,
				(bool, int, Iterable),
			)
	def proc_children(self, items: Sequence):
		return [items[c] for c in self.conditions if c < len(items)]

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

	class PipelineTest(Test):
		def test1(self):
			Pipeline(
				Pipeline(
					Task(demo_task_1),
					Task(demo_task_2),
				),
				demo_task_3,
				Task(demo_task_4),
			)()
			Pipeline(
				Pipeline(
					Task(demo_task_1),
				),
				Pipeline(
					Task(demo_task_2),
					demo_task_5,
				),
			)()
		def test2(self):
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
			)()
		def test3(self):
			Multiplexer(
				[2,3,0],
				Pipeline(
					Task(demo_task_2),
					demo_task_5,
				),
				Pipeline(
					Task(demo_task_1),
				),
				Pipeline(
					Task(demo_task_4),
				),
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
				id = "a",
			)()

		def test4(self):
			def subfunc():
				print("We are in subfunc!")
				Pipeline(
					demo_task_3,
					Task(demo_task_4),
					id="a",
				)()
				Pipeline(
					Pipeline(
						Task(demo_task_1),
						Task(demo_task_2),
					),
				)()
			Pipeline(
				Pipeline(
					Task(demo_task_1),
					Task(demo_task_2),
				),
				Task(subfunc),
			)()
		def inf_loop(self):
			def subfunc():
				print("We are in subfunc!")
				Pipeline(
					demo_task_3,
					Task(demo_task_4),
					id=31,
				)()
				Pipeline(
					Pipeline(
						Task(demo_task_1),
						Task(subfunc),
					),
				)()
			Pipeline(
				Pipeline(
					Task(demo_task_1),
					Task(demo_task_2),
					id="b",
				),
				Task(subfunc),
				id="a"
			)()
		def test5(self):
			Task(demo_task_1)()
	test=PipelineTest()
	test.test5()
