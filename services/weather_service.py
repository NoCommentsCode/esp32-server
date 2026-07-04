# services/weather_service.py
import urequests
import json
import time
from utils.logger import logger
from config import Config
import _thread

class WeatherService:
    """Сервис для получения данных о погоде с WeatherAPI"""
    
    def __init__(self):
        self.api_key = Config.WEATHER_API_KEY
        self.city = Config.WEATHER_CITY
        self.lang = Config.WEATHER_LANG
        self.update_interval = Config.WEATHER_UPDATE_INTERVAL
        self.last_update = 0
        self.cached_data = None
        self.base_url = "https://api.weatherapi.com/v1/current.json"
        # Автоматическое обновление отключено по умолчанию
        self.auto_update_enabled = False
        
    def get_weather(self, force_update=False):
        """
        Получение текущей погоды
        Args:
            force_update: принудительное обновление (игнорирует кэш)
        Returns:
            dict: словарь с данными о погоде или None при ошибке
        """
        current_time = time.time()
        
        # Проверяем кэш
        if not force_update and self.cached_data:
            if current_time - self.last_update < self.update_interval:
                logger.debug("Returning cached weather data")
                return self.cached_data
        
        # Запрашиваем новые данные
        logger.info("Fetching weather data from API...")
        data = self._fetch_from_api()
        
        if data:
            self.cached_data = data
            self.last_update = current_time
            logger.info("Weather data updated successfully")
        else:
            logger.warning("Using cached weather data (API failed)")
            # Если API не отвечает, возвращаем кэшированные данные (даже если старые)
            if self.cached_data:
                logger.info("Returning stale cached data")
                return self.cached_data
        
        return data
    
    def _fetch_from_api(self):
        """Внутренний метод для запроса к WeatherAPI"""
        try:
            # Формируем URL
            url = f"{self.base_url}?q={self.city}&lang={self.lang}&key={self.api_key}"
            
            logger.debug(f"Requesting: {url.replace(self.api_key, '***')}")
            
            # Выполняем запрос
            response = urequests.get(url, timeout=Config.WEATHER_API_TIMEOUT)
            
            # Проверяем статус
            if response.status_code == 200:
                # Парсим ответ
                raw_data = response.json()
                processed_data = self._process_response(raw_data)
                response.close()
                return processed_data
            else:
                logger.error(f"Weather API error: {response.status_code}")
                response.close()
                return None
                
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return None
    
    def _process_response(self, raw_data):
        """
        Обработка сырого ответа от API
        Извлекаем только нужные поля
        """
        try:
            current = raw_data.get('current', {})
            location = raw_data.get('location', {})
            
            # Преобразуем давление из мбар в мм рт. ст. (1 мбар = 0.750062 мм рт. ст.)
            pressure_mb = current.get('pressure_mb', 0)
            pressure_mm = round(pressure_mb * 0.750062, 1)
            
            weather_data = {
                'location': {
                    'name': location.get('name', 'Unknown'),
                    'country': location.get('country', 'Unknown'),
                    'localtime': location.get('localtime', 'Unknown')
                },
                'current': {
                    'temp_c': current.get('temp_c'),
                    'humidity': current.get('humidity'),
                    'pressure_mb': pressure_mb,
                    'pressure_mm': pressure_mm,
                    'condition_text': current.get('condition', {}).get('text', 'Unknown'),
                    'condition_icon': current.get('condition', {}).get('icon', ''),
                    'wind_kph': current.get('wind_kph'),
                    'feelslike_c': current.get('feelslike_c'),
                    'is_day': current.get('is_day', 1),
                    'last_updated': current.get('last_updated', 'Unknown')
                },
                'timestamp': time.time()
            }
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Error processing weather data: {str(e)}")
            return None
    
    def get_cached_weather(self):
        """Получить кэшированные данные без обновления"""
        return self.cached_data
    
    def force_update(self):
        """Принудительное обновление данных"""
        return self.get_weather(force_update=True)
    
    def start_auto_update(self):
        """Запуск автоматического обновления в отдельном потоке"""
        if not self.auto_update_enabled:
            self.auto_update_enabled = True
            _thread.start_new_thread(self._auto_update_loop, ())
            logger.info("Auto-update started")
    
    def stop_auto_update(self):
        """Остановка автоматического обновления"""
        self.auto_update_enabled = False
        logger.info("Auto-update stopped")
    
    def _auto_update_loop(self):
        """Цикл автоматического обновления"""
        while self.auto_update_enabled:
            time.sleep(self.update_interval)
            if self.auto_update_enabled:
                logger.debug("Auto-updating weather data...")
                self.get_weather(force_update=True)