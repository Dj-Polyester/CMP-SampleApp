import argparse, os
from pathlib import Path
import sys
from jproperties import Properties
from typing import Callable

from tasks import log, Task, Pipeline, Multiplexer
from tasks.utils import multitype, _bool

VALID_VERBOSE_VALUES = [
	"VERBOSE",
	"SILENT",
	"DEBUG",
	"INFO",
	"WARNING",
	"ERROR",
	"CRITICAL",
]

class FileActor:
	@classmethod
	def ask(cls, prompt: str):
		log.print(f"Contents of {cls.file_path}:")
		log.print(cls.f.read())
		res: str=input(f"{prompt} (y/N)?: ")
		return res.lower()
	@classmethod
	def act_prompted(
		cls,
		file_path: Path,
		prompt: str,
		condition: Callable = lambda _: True,
		*args,
		**kwargs
	) -> bool:
		cls.file_path = file_path
		with open(cls.file_path, "r+b") as cls.f:
			cls.preact(*args, **kwargs)
			if condition(cls):
				res = cls.ask(prompt)
				if res == "y":
					cls.acty(*args, **kwargs)
				else:
					cls.actn(*args, **kwargs)
			cls.postact(*args, **kwargs)
		return True
	@classmethod
	def preact(cls, *_, **__):
		raise NotImplementedError()
	@classmethod
	def acty(cls, *_, **__):
		raise NotImplementedError()
	@classmethod
	def actn(cls, *_, **__):
		raise NotImplementedError()
	@classmethod
	def postact(cls, *_, **__):
		raise NotImplementedError()

class PropertyActor(FileActor):
	p = Properties()
	@classmethod
	def preact(cls, *_, **__):
		cls.p.reset()
		cls.p.clear()
		cls.p.load(cls.f, "utf-8")
	@classmethod
	def acty(cls, *_, **custom_properties):
		cls.p.properties = {**cls.p.properties,**custom_properties}
		cls.f.seek(0)
		cls.f.truncate(0)
		cls.p.store(cls.f, encoding="utf-8")
	@classmethod
	def actn(cls, *_, **__):
		pass
	@classmethod
	def postact(cls, *_, **__):
		pass
	@classmethod
	def exists_equal(cls, property: str, target: str):
		return property in cls.p and cls.p[property].data == target

# Preprocessing utils
def touch(file_path: Path):
	file_path.touch()
# Other utils
def runProcess(cmd: str, use_mp = False):
	log.print(cmd)
	Task(cmd, use_mp=use_mp)()
def install(file_path: Path):
	wiredFlag = None
	wiredMsg = None
	if args.wired:
		wiredMsg = "via USB"
		wiredFlag = "d"
	else:
		wiredMsg = "wirelessly or to the emulator"
		wiredFlag = "e"
	print(f"Installing {wiredMsg}:")
	runProcess(f"adb -{wiredFlag} install {file_path}")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="android_debug",
		description="Builds, installs and runs APK file",
	)
	parser.add_argument(
		"--package_name",
		type=str,
		default="org.example.project",
		metavar="(str, default: org.custom.slide)",
		help=
"Package name that includes the entry point (i.e. MainActivity.kt)"
"of the application when debugging via adb. This is typically the"
"first package name chosen before creating the project directory."
	)
	parser.add_argument(
		"--log_tag",
		type=str,
		metavar="(str, default=ComposeApp)",
		default="ComposeApp",
		help=
"The tag used by the Log instances. Logcat will only print the logs with this tag."
	)
	parser.add_argument(
		"--subproject",
		type=str,
		metavar="(str, default=composeApp)",
		default="composeApp",
		help=
"Name used for the build directory, where the APK files are stored."
"The build directory is [subproject]/build/outputs/apk/debug/[subproject]-debug.apk."
	)
	parser.add_argument(
		"-w",
		"--wired",
		type=_bool,
		metavar="(bool, default=True)",
		default=True,
		help=
"Whether to use wired connection or not."
"Value of 1 will attempt to debug the device connected via USB "
"whereas 0 will try either the device connected wirelessly or an"
"emulator running. Debugging multiple devices is not possible."
	)
	parser.add_argument(
		"-p",
		"--preprocess",
		type=_bool,
		metavar="(bool, default=False)",
		default=False,
		help=
"Prompts the user for series of manual handling to"
"remove warnings/errors. "
"In some cases, the program may automatically handle its prompts."
	)
	parser.add_argument(
		"-a",
		"--assemble",
		type=_bool,
		metavar="(bool, default=True)",
		default=True,
		help=
"Whether to assemble the project and generate APK files."
	)
	parser.add_argument(
		"-i",
		"--install",
		type=_bool,
		metavar="(bool, default=True)",
		default=True,
		help=
"Whether to install the APK."
	)
	parser.add_argument(
		"-r",
		"--run",
		type=_bool,
		metavar="(bool, default=True)",
		default=True,
		help=
"Whether to run the installed APK. The logs will be printed."
	)
	parser.add_argument(
		"-v",
		"--verbose",
		type=multitype(int, str),
		metavar="(int or str, default=warning)",
		default="warning",
		help=
"Choose a verbose level, either integer or string."
"Each given level corresponds to a logging level used in standard libraries"
"and integer: string values are as follows:"
"\n1: debug,"
"\n2: info,"
"\n3: warning,"
"\n4: error,"
"\n5: critical,"
"for string values, 'verbose' and 'silent' values are also available."
	)
	args = parser.parse_args()

	verbose_lwl: int = 0
	if isinstance(args.verbose, int):
		verbose_lwl = args.verbose * 10
	elif args.verbose.upper() in VALID_VERBOSE_VALUES:
		verbose_lwl = getattr(log, args.verbose.upper())
	log.setLevel(verbose_lwl)
	print(f"Log level {log.getEffectiveLevel()}")
	log.print(f"Arguments:\n{args}")

	subproject: str = args.subproject
	android_home = os.environ.get("ANDROID_HOME")
	android_debug = Pipeline(
		Multiplexer(
			args.preprocess,
			Pipeline(
				#Change sdk.dir in local.properties to Android SDK location to suppress the warning
				Task(
					PropertyActor.act_prompted,
					file_path=Path("local.properties"),
					prompt=f"Update your SDK path {android_home} in local.properties",
					condition = lambda c: not c.exists_equal("sdk.dir", android_home),
					**{"sdk.dir": android_home},
				),
				#Add kotlin.native.ignoreDisabledTargets=true to suppress the warning
				Task(
					PropertyActor.act_prompted,
					file_path=Path("gradle.properties"),
					prompt="Ignore disabled targets",
					condition = lambda c: not c.exists_equal("kotlin.native.ignoreDisabledTargets", "true"),
					**{"kotlin.native.ignoreDisabledTargets": "true"},
				),
				# copyNonXmlValueResourcesForCommonMain task failed with timestamp error on a file.
				# touch updates the timestamp of the file resolving the issue.
				Task(
					touch,
					Path(
						subproject, "src", "commonMain", "composeResources", "drawable"
					),
				),
				id="preprocess",
			),
			id="preprocess",
		),
		Multiplexer(
			args.assemble,
			Task(
				runProcess,
				f"./gradlew :{subproject}:assembleDebug",
				use_mp=True,
			),
			id="assemble",
		),
		Multiplexer(
			args.install,
			Pipeline(
				Task(
					runProcess,
					"adb devices",
				),
				Task(
					install,
					Path(subproject, "build", "outputs", "apk", "debug", f"{subproject}-debug.apk"),
				),
				id="install",
			),
			id="install",
		),
		Multiplexer(
			args.run,
			Pipeline(
				Task(
					runProcess,
					f"adb shell am start -a android.intent.action.MAIN -n {args.package_name}/.MainActivity",
				),
				Task(
					runProcess,
					f"adb logcat {args.log_tag}:D *:S",
				),
				id="run",
			),
			id="run",
		),
		verbose = log.level(log.VERBOSE),
		id="android_debug",
	)
	android_debug()
