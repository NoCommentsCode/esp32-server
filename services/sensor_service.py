# services/sensor_service.py
import time

class SensorService:
    """Сервис для работы с датчиками"""
    
    def __init__(self):
        # Здесь можно инициализировать датчики
        self.sensors = {}
        self.settings = {
            'read_interval': 5,  # секунд
            'enabled': True
        }
        
    def read_all(self):
        """Чтение всех датчиков"""
        # Заглушка - возвращаем тестовые данные
        return {
            'temperature': self._read_temperature(),
            'humidity': self._read_humidity(),
            'pressure': self._read_pressure(),
            'timestamp': time.time()
        }
    
    def read_sensor(self, sensor_name):
        """Чтение конкретного датчика"""
        if sensor_name == 'temperature':
            return self._read_temperature()
        elif sensor_name == 'humidity':
            return self._read_humidity()
        elif sensor_name == 'pressure':
            return self._read_pressure()
        else:
            return None
    
    def update_settings(self, settings):
        """Обновление настроек датчиков"""
        for key, value in settings.items():
            if key in self.settings:
                self.settings[key] = value
        return True
    
    def _read_temperature(self):
        """Заглушка: чтение температуры"""
        # В реальном проекте здесь было бы чтение с датчика
        return 25.5
    
    def _read_humidity(self):
        """Заглушка: чтение влажности"""
        return 60.0
    
    def _read_pressure(self):
        """Заглушка: чтение давления"""
        return 1013.25