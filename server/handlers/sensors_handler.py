# server/handlers/sensors_handler.py
import json
from models.response import HttpResponse
from utils.logger import logger

class SensorsHandler:
    """Обработчик эндпоинта /sensors"""
    
    def __init__(self, sensor_service):
        self.sensor_service = sensor_service
    
    def handle_get(self, request):
        """GET /sensors - получить все данные с датчиков"""
        try:
            # Метод GET уже проверен в router, здесь не нужно
            sensors_data = self.sensor_service.read_all()
            return HttpResponse(
                status_code=200,
                data={'sensors': sensors_data}
            )
        except Exception as e:
            logger.error("Error reading sensors: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot read sensors: " + str(e)
            )
    
    def handle_post(self, request):
        """POST /sensors - изменить настройки датчиков"""
        try:
            # Метод POST уже проверен в router, здесь не нужно
            body = request.get('body', '{}')
            
            try:
                data = json.loads(body)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )
            
            # Обновляем настройки
            result = self.sensor_service.update_settings(data)
            
            return HttpResponse(
                status_code=200,
                data={'result': result}
            )
        except Exception as e:
            logger.error("Error updating sensor settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot update settings: " + str(e)
            )