import logging
from utils import Singleton, exists
class Log(Singleton):
	"""
	Wrapper around `logging` package
	"""
	VERBOSE_LEVEL = logging.DEBUG
	SILENT_LEVEL = logging.INFO
	def __init__(self):
		logging.basicConfig(
    		level=logging.INFO,                     # Set minimum log level
    		format="%(asctime)s - %(levelname)s - %(message)s"
		)
		self._logger = logging.getLogger()
	def verbose(self) -> bool:
		return self.getEffectiveLevel() <= self.VERBOSE_LEVEL
	def set_verbosity(self, val:bool = True):
		self._logger.setLevel(self.VERBOSE_LEVEL if val else self.SILENT_LEVEL)
	def print(self,*args, **kwargs):
		if self.verbose():
			print(*args, **kwargs)
	def __getattr__(self, name: str):
		if exists(logging, name):
			return getattr(logging, name)
		elif exists(self._logger, name):
			return getattr(self._logger, name)
		else:
			raise AttributeError(
				f"Attribute {name} should either be "
				f"in `logging` module or `Logger` object"
			)

log = Log()
