import logging
import reprlib
from test import Test
from utils import Attrs, Param, Singleton
import pprint as pp
class Log(Singleton):
	"""
	Wrapper around `logging` package
	"""
	LONG = 64
	VERBOSE = logging.INFO
	SILENT = logging.WARNING
	def __init__(self, shorten = False):
		logging.basicConfig(
    		level=self.INFO,                     # Set minimum log level
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
	def repr(self, _repr: str):
		if self.shorten and self.level(self.DEBUG):
			_repr = reprlib.repr(_repr)
		if len(_repr) > self.LONG:
			_repr = pp.pformat(_repr)
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
