# utils/logger.py
import time
from config import Config

class Logger:
    """Простая система логирования"""
    
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    
    LEVEL_NAMES = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARNING: 'WARNING',
        ERROR: 'ERROR'
    }
    
    def __init__(self, level=INFO):
        self.level = level
    
    def _log(self, level, message):
        """Внутренний метод логирования"""
        if level >= self.level:
            timestamp = time.localtime()
            time_str = f"{timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
            print(f"[{time_str}] [{self.LEVEL_NAMES[level]}] {message}")
    
    def debug(self, message):
        self._log(self.DEBUG, message)
    
    def info(self, message):
        self._log(self.INFO, message)
    
    def warning(self, message):
        self._log(self.WARNING, message)
    
    def error(self, message):
        self._log(self.ERROR, message)

# Глобальный экземпляр
logger = Logger(level=Logger.DEBUG if Config.DEBUG else Logger.INFO)