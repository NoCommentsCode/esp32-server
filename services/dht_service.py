# services/dht_service.py
import dht
import machine
import time
from utils.logger import logger

class DHTService:
    """Сервис для работы с датчиком DHT22"""
    
    def __init__(self, pin_number=14):
        """
        Инициализация DHT22 датчика
        
        Args:
            pin_number: номер GPIO пина, к которому подключен DATA
        """
        self.pin_number = pin_number
        self.sensor = None
        self.last_read_time = 0
        self.last_temperature = None
        self.last_humidity = None
        self._init_sensor()
    
    def _init_sensor(self):
        """Инициализация сенсора"""
        try:
            pin = machine.Pin(self.pin_number)
            self.sensor = dht.DHT22(pin)
            logger.info(f"DHT22 initialized on pin {self.pin_number}")
        except Exception as e:
            logger.error(f"Failed to initialize DHT22: {e}")
            self.sensor = None
    
    def read(self, force=False):
        """
        Чтение данных с датчика
        
        Args:
            force: принудительное чтение (игнорирует интервал 2 секунды)
            
        Returns:
            dict: {'temperature': float, 'humidity': float} или None при ошибке
        """
        if self.sensor is None:
            return None
        
        current_time = time.ticks_ms()
        
        # DHT22 требует минимум 2 секунды между измерениями [citation:2][citation:5]
        if not force and time.ticks_diff(current_time, self.last_read_time) < 2000:
            # Возвращаем последние данные, если интервал меньше 2 секунд
            if self.last_temperature is not None:
                return {
                    'temperature': self.last_temperature,
                    'humidity': self.last_humidity,
                    'cached': True
                }
        
        try:
            self.sensor.measure()
            temp = self.sensor.temperature()
            hum = self.sensor.humidity()
            
            # Проверка на валидность данных
            if temp is not None and hum is not None:
                self.last_temperature = temp
                self.last_humidity = hum
                self.last_read_time = current_time
                
                logger.debug(f"DHT22 read: {temp}°C, {hum}%")
                
                return {
                    'temperature': temp,
                    'temperature_f': temp * 9/5 + 32,  # Фаренгейт
                    'humidity': hum,
                    'cached': False
                }
            else:
                logger.warning("DHT22 returned None values")
                return None
                
        except OSError as e:
            # Ошибка чтения (часто бывает при первом чтении)
            logger.error(f"DHT22 read error: {e}")
            return None
        except Exception as e:
            logger.error(f"DHT22 unexpected error: {e}")
            return None
    
    def get_status(self):
        """Получить статус датчика"""
        return {
            'initialized': self.sensor is not None,
            'pin': self.pin_number,
            'last_temperature': self.last_temperature,
            'last_humidity': self.last_humidity,
            'last_read_time': self.last_read_time
        }