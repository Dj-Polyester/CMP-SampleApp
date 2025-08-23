import argparse, os, sys, subprocess, time
from subprocess import CompletedProcess
from types import NoneType
from typing import Union, Callable, Iterable
from pathlib import Path
from jproperties import Properties
from dataclasses import dataclass

class FileActor:
	@classmethod
	def ask(cls, prompt: str):
		if args.verbose:
			print(f"Contents of {cls.file_path}:")
			print(cls.f.read())
		res: str=input(f"{prompt} (y/N)?: ")
		return res.lower()
	@classmethod
	def act_prompted(
		cls,
		file_path: Path,
		prompt: str,
		condition: Callable = lambda _: True,
		*act_args,
		**act_kwargs
	) -> bool:
		cls.file_path = file_path
		with open(cls.file_path, "r+b") as cls.f:
			cls.preact()
			if condition(cls):
				res = cls.ask(prompt)
				if res == "y":
					cls.act(*act_args, **act_kwargs)
					cls.postact()
		return True
	@classmethod
	def preact(cls, *_, **__):
		raise NotImplementedError()
	@classmethod
	def act(cls, *_, **__):
		raise NotImplementedError()
	@classmethod
	def postact(cls, *_, **__):
		raise NotImplementedError()

class PropertyActor(FileActor):
	p = Properties()
	@classmethod
	def preact(cls):
		cls.p.reset()
		cls.p.clear()
		cls.p.load(cls.f, "utf-8")
	@classmethod
	def act(cls, custom_properties: dict):
		cls.p.properties = {**cls.p.properties,**custom_properties}
	@classmethod
	def postact(cls):
		cls.f.seek(0)
		cls.f.truncate(0)
		cls.p.store(cls.f, encoding="utf-8")
	@classmethod
	def exists_equal(cls, property: str, target: str):
		return property in cls.p and cls.p[property].data == target
@dataclass
class CompletedStep:
	exitcode: int
	elapsed_time: float
class Step:
	def __init__(self, callback: Callable, _id=None, *args, **kwargs):
		self.callback = callback
		self.args = args
		self.kwargs = kwargs
		self.id = _id
	def invoke(self) -> Union[bool, CompletedProcess]:
		return self.callback(*self.args, **self.kwargs)
	def __call__(self):
		start = time.perf_counter()
		exitcode: int = 0
		try:
			res = self.invoke()
			if isinstance(res, CompletedProcess):
				exitcode = res.returncode
			elif isinstance(res, bool):
				exitcode = int(not res)
			else:
				raise TypeError(f"The callable returns value of type {type(res)}")
		except KeyboardInterrupt:
			exitcode = 1
		return CompletedStep(exitcode, time.perf_counter() - start)
class Steps:
	def __init__(self, id=None, *steps: Iterable[Step]):
		self.id = id
		if len(steps) == 1 and isinstance(steps[0], Iterable):
			self.steps = steps[0]
		else:
			self.steps = steps
	def __call__(self) -> CompletedStep:
		elapsed_time = 0
		try:
			res: Union[CompletedStep, NoneType] = None
			for step in self.steps:
				if isinstance(step, Step):
					res = step()
					if isinstance(res, CompletedStep):
						elapsed_time += res.elapsed_time
						if res.exitcode:
							return CompletedStep(res.exitcode, elapsed_time)
					else:
						raise TypeError(f"Step object returns the wrong type {type(res)}")
				else:
					raise TypeError(f"The object is not of Step type but {type(step)}")
		except KeyboardInterrupt:
			pass
		return CompletedStep(1, elapsed_time)
# Preprocessing utils
def touch(file_path: Path) -> bool:
	file_path.touch()
	return True
# Other utils
def runProcess(cmd: str, **kwargs) -> CompletedProcess:
	if args.verbose:
		print(cmd)
	cmdList = cmd.split()
	return subprocess.run(cmdList, **kwargs)
def install(file_path: Path) -> CompletedProcess:
	wiredFlag = None
	wiredMsg = None
	if args.wired:
		wiredMsg = "via USB"
		wiredFlag = "d"
	else:
		wiredMsg = "wirelessly or to the emulator"
		wiredFlag = "e"
	print(f"Installing {wiredMsg}:")
	return runProcess(f"adb -{wiredFlag} install {file_path}")

def android_debug():
	if args.preprocess:
		android_home = os.environ.get("ANDROID_HOME")
		print("Preprocessing:")
		Step.iter(
			#Change sdk.dir in local.properties to Android SDK location to suppress the warning
			Step(
				PropertyActor.act_prompted,
				file_path=Path("local.properties"),
				prompt=f"Update your SDK path {android_home} in local.properties",
				custom_properties={"sdk.dir": android_home},
				condition = lambda c: not c.exists_equal("sdk.dir", android_home),
			),
			#Add kotlin.native.ignoreDisabledTargets=true to suppress the warning
			Step(
				PropertyActor.act_prompted,
				file_path=Path("gradle.properties"),
				prompt="Ignore disabled targets",
				custom_properties={"kotlin.native.ignoreDisabledTargets": "true"},
				condition = lambda c: not c.exists_equal("kotlin.native.ignoreDisabledTargets", "true"),
			),
			# copyNonXmlValueResourcesForCommonMain task failed with timestamp error on a file.
			# touch updates the timestamp of the file resolving the issue.
			Step(
				touch,
				file_path=Path(
					subproject, "src", "commonMain", "composeResources", "drawable"
				),
			),
		)
	times = {}
	try:
		if args.assemble:
			print("Assembling:")
			assemble_res = Step(
				runProcess,
				f"./gradlew :{subproject}:assembleDebug",
			)()
			times["Assemble"] = assemble_res.elapsed_time
			if assemble_res.exitcode:
				return times
		if args.install:
			install_res = Step.iter(
				Step(
					runProcess,
					"adb devices",
				),
				Step(
					install,
					Path(subproject, "build", "outputs", "apk", "debug", f"{subproject}-debug.apk"),
				),
			)
			times["Install"] = install_res.elapsed_time
			if install_res.exitcode:
				return times
		if args.run:
			print("Running:")
			run_res = Step.iter(
				Step(
					runProcess,
					f"adb shell am start -a android.intent.action.MAIN -n {args.package_name}/.MainActivity",
				),
				# Clear the logs
				Step(
					runProcess,
					"adb logcat -c",
				),
				# Show the logs with log_tag
				Step(
					runProcess,
					f"adb logcat {args.log_tag}:D *:S",
				),
			)
			times["Run"] = run_res.elapsed_time
			if run_res.exitcode:
				return times
	except KeyboardInterrupt:
		pass
	return times
def print_perf_res(times):
	if args.assemble or args.install or args.run:
		print("Performance results:")
	total_time = 0
	for k, v in times.items():
		print(f"{k}: {v} seconds")
		total_time += v
		print(f"Total: {total_time} seconds")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog='android_debug',
		description='Builds, installs and runs APK file',
	)
	parser.add_argument(
		'--package_name',
		type=str,
		default="org.custom.slide",
		help="""
Package name that includes the entry point (i.e. MainActivity.kt)
of the application when debugging via adb. This is typically the
first package name chosen before creating the project directory.
	""")
	parser.add_argument(
		'--log_tag',
		type=str,
		default="ComposeApp",
		help="""
The tag used by the Log instances. Logcat will only print the logs
with this tag. Default is "ComposeApp"
	""")
	parser.add_argument(
		'--subproject',
		type=str,
		default="composeApp",
		help="""
Name used for the build directory, where the APK files are stored.
Default is "composeApp". The build directory is
[subproject]/build/outputs/apk/debug/[subproject]-debug.apk.
	""")
	parser.add_argument(
		'-w',
		'--wired',
		type=int,
		default=1,
		help="""
Whether to use wired connection or not.
Value of 1 will attempt to debug the device connected via USB
whereas 0 will try either the device connected wirelessly or an
emulator running. Debugging multiple devices is not possible.
Default is 1.
	""")
	parser.add_argument(
		'-v',
		'--verbose',
		type=int,
		default=0,
		help="""
Prints the commands run.
	""")
	parser.add_argument(
		'-p',
		'--preprocess',
		type=int,
		default=0,
		help="""
Urges the user for a number of preprocessing steps to
remove warnings/errors. Default is 0.
	""")
	parser.add_argument(
		'-a',
		'--assemble',
		type=int,
		default=1,
		help="""
Whether to assemble the project and generate APK files. Default is 1.
	""")
	parser.add_argument(
		'-i',
		'--install',
		type=int,
		default=1,
		help="""
Whether to install the APK. Default is 1.
	""")
	parser.add_argument(
		'-r',
		'--run',
		type=int,
		default=1,
		help="""
Whether to run the installed APK. The logs will be printed. Default is 1.
	""")

	args = parser.parse_args()
	subproject: str = args.subproject
	if args.verbose:
		print("Arguments:")
		print(args)
	print_perf_res(android_debug())
