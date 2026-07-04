# server/handlers/dht_handler.py
from models.response import HttpResponse
from utils.logger import logger

class DHTHandler:
    """Обработчик эндпоинтов для DHT22 датчика"""
    
    def __init__(self, dht_service):
        self.dht_service = dht_service
    
    def handle_get_sensor(self, request):
        """
        GET /sensor/dht - получить текущие показания датчика
        
        Опциональные query параметры:
        - force=true - принудительное чтение (игнорирует кэш)
        """
        try:
            # Проверяем метод
            if request.get('method') != 'GET':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )
            
            # Получаем query параметры
            query = request.get('query', {})
            force = query.get('force', '').lower() == 'true'
            
            # Читаем датчик
            data = self.dht_service.read(force=force)
            
            if data is None:
                return HttpResponse(
                    status_code=500,
                    error="Failed to read from DHT22 sensor"
                )
            
            # Формируем ответ
            response_data = {
                'temperature_celsius': round(data['temperature'], 1),
                'temperature_fahrenheit': round(data['temperature_f'], 1),
                'humidity_percent': round(data['humidity'], 1),
                'cached': data.get('cached', False)
            }
            
            # Добавляем метаданные
            meta = {
                'sensor_type': 'DHT22',
                'pin': self.dht_service.pin_number,
                'timestamp': self.dht_service.last_read_time
            }
            
            return HttpResponse(
                status_code=200,
                data={'sensor': response_data, 'meta': meta}
            )
            
        except Exception as e:
            logger.error(f"Error in DHT handler: {e}")
            return HttpResponse(
                status_code=500,
                error=f"Internal error: {str(e)}"
            )
    
    def handle_get_status(self, request):
        """
        GET /sensor/dht/status - получить статус датчика
        """
        try:
            status = self.dht_service.get_status()
            
            return HttpResponse(
                status_code=200,
                data=status
            )
            
        except Exception as e:
            logger.error(f"Error in DHT status: {e}")
            return HttpResponse(
                status_code=500,
                error=f"Internal error: {str(e)}"
            )