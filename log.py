import logging
import reprlib
from typing import Any
from test import Test
from utils import Attrs, Param, Singleton, stringify_map
import pprint as pp
import black

class Log(Singleton):
	"""
	Wrapper around `logging` package
	"""
	VERBOSE = logging.INFO
	SILENT = logging.WARNING
	def __init__(
		self,
		shorten = False,
	):
		logging.basicConfig(
    		level=Log.VERBOSE,                     # Set minimum log level
    		format="%(asctime)s:%(levelname)s:%(message)s"
		)
		self.shorten = shorten
		self._logger = logging.getLogger()
	def level(self, _level) -> bool:
		return self.getEffectiveLevel() <= _level
	def verbose(self):
		return self.level(self.VERBOSE)
	def set_verbosity(self, val:bool = True):
		self._logger.setLevel(self.VERBOSE if val else self.SILENT)
	def print(self, *args, _level=Param.DEFAULT, **kwargs):
		if _level == Param.DEFAULT:
			_level = self.getEffectiveLevel()
		if self.level(_level):
			print(*args, **kwargs)
	def repr(self, _repr: Any):
		if self.shorten and self.level(self.DEBUG):
			_repr = reprlib.repr(_repr)
		_repr = black.format_str(str(_repr), mode=black.FileMode())
		return _repr
	def __getattr__(self, name: str):
		if Attrs.has(logging, name):
			return getattr(logging, name)
		elif Attrs.has(self._logger, name):
			return getattr(self._logger, name)
		else:
			raise AttributeError(
				f"Attribute {name} should either be "
				f"in `logging` module or `Logger` object"
			)

log = Log()

if __name__ == "__main__":
	class LogTest(Test):
		def test_repr(self):
			dummy_dic = {
				231576523: 81347234,
				"sydtysfdydf": True,
				"asdsadsd": 8932642938,
				"dfdfdfd": "2938432947",
				2316523: 81347234,
				"sydsfdydf": True,
				"asdssd": 8932642938,
				"dffdfd": "2938432947",
				2315763: 81347234,
				"sydtfdydf": True,
				"asdsdsd": 8932642938,
				"dfdfd": "2938432947",
			}
			print(log.repr(f"Type({stringify_map(dummy_dic)})"))
	log_test = LogTest()
	log_test()
