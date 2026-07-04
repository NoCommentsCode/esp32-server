# server/handlers/settings_handler.py
import json
from models.response import HttpResponse
from utils.logger import logger

class SettingsHandler:
    """Обработчик эндпоинтов для настроек"""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
    
    def handle_get_settings(self, request):
        """GET /settings - получить все настройки"""
        try:
            settings = self.storage_service.get_settings()
            return HttpResponse(
                status_code=200,
                data=settings
            )
        except Exception as e:
            logger.error("Error in get settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot read settings: " + str(e)
            )
    
    def handle_update_settings(self, request):
        """POST /settings - обновить настройки"""
        try:
            body = request.get('body', '{}')
            
            try:
                new_settings = json.loads(body)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )
            
            # Обновляем настройки
            result = self.storage_service.update_settings(new_settings)
            
            return HttpResponse(
                status_code=200,
                data={'result': result, 'settings': self.storage_service.get_settings()}
            )
        except Exception as e:
            logger.error("Error in update settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot update settings: " + str(e)
            )
    
    def handle_reset_settings(self, request):
        """DELETE /settings - сбросить настройки"""
        try:
            self.storage_service.reset_settings()
            return HttpResponse(
                status_code=200,
                data={'result': 'Settings reset to defaults'}
            )
        except Exception as e:
            logger.error("Error in reset settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot reset settings: " + str(e)
            )