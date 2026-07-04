# server/handlers/weather_handler.py
from models.response import HttpResponse
from utils.logger import logger

class WeatherHandler:
    """Обработчик эндпоинтов для погоды"""
    
    def __init__(self, weather_service):
        self.weather_service = weather_service
    
    def handle_get_weather(self, request):
        """GET /weather - получить текущую погоду"""
        try:
            # Проверяем метод
            if request.get('method') != 'GET':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )
            
            # Получаем параметры запроса
            query = request.get('query', {})
            force = query.get('force', '').lower() == 'true'
            
            # Получаем данные о погоде
            weather_data = self.weather_service.get_weather(force_update=force)
            
            if not weather_data:
                return HttpResponse(
                    status_code=503,
                    error="Weather data unavailable. Please try again later."
                )
            
            # Добавляем метаинформацию
            response_data = {
                'weather': weather_data,
                'meta': {
                    'cached': not force and self.weather_service.cached_data is not None,
                    'timestamp': weather_data.get('timestamp'),
                    'update_interval': self.weather_service.update_interval
                }
            }
            
            return HttpResponse(
                status_code=200,
                data=response_data
            )
            
        except Exception as e:
            logger.error("Error in weather handler: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot get weather data: " + str(e)
            )
    
    def handle_refresh_weather(self, request):
        """POST /weather/refresh - принудительное обновление погоды"""
        try:
            if request.get('method') != 'POST':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use POST"
                )
            
            # Принудительно обновляем
            weather_data = self.weather_service.force_update()
            
            if not weather_data:
                return HttpResponse(
                    status_code=503,
                    error="Failed to refresh weather data"
                )
            
            return HttpResponse(
                status_code=200,
                data={
                    'message': 'Weather data refreshed',
                    'weather': weather_data,
                    'timestamp': weather_data.get('timestamp')
                }
            )
            
        except Exception as e:
            logger.error("Error refreshing weather: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot refresh weather: " + str(e)
            )