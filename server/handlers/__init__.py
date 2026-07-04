# server/handlers/__init__.py
"""
Пакет обработчиков HTTP запросов
"""
# В MicroPython нельзя использовать относительные импорты через точку
# Используем абсолютные импорты

from server.handlers.info_handler import InfoHandler
from server.handlers.sensors_handler import SensorsHandler
from server.handlers.gpio_handler import GPIOHandler
from server.handlers.settings_handler import SettingsHandler
from server.handlers.system_handler import SystemHandler

# Определяем, что экспортируется
__all__ = [
    'InfoHandler',
    'SensorsHandler', 
    'GPIOHandler',
    'SettingsHandler',
    'SystemHandler'
]