# server/handlers/info_handler.py
import gc
import os
import sys
import machine
from models.response import HttpResponse
from services.device_service import DeviceService
from utils.logger import logger

class InfoHandler:
    """Обработчик эндпоинта /info"""
    
    def __init__(self, device_service):
        self.device_service = device_service
    
    def handle(self, request):
        """Обработка GET /info"""
        try:
            # Проверяем метод
            if request.get('method') != 'GET':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )
            
            # Собираем информацию
            device_info = self.device_service.get_device_info()
            
            # Возвращаем успешный ответ
            return HttpResponse(
                status_code=200,
                data=device_info
            )
        except Exception as e:
            logger.error("Error in info handler: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: " + str(e)
            )