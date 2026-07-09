# server/handlers/settings_handler.py
import json
from models.response import HttpResponse
from utils.logger import logger


class SettingsHandler:
    """Обработчик эндпоинтов для настроек станции."""

    def __init__(self, settings_service):
        self.settings_service = settings_service

    def handle_get_settings(self, request):
        """GET /settings - получить изменяемые настройки."""
        try:
            if request.get('method') != 'GET':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            return HttpResponse(
                status_code=200,
                data=self.settings_service.get_settings()
            )
        except Exception as e:
            logger.error("Error in get settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot read settings: " + str(e)
            )

    def handle_update_settings(self, request):
        """POST /settings - обновить настройки."""
        try:
            if request.get('method') != 'POST':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use POST"
                )

            body = request.get('body', '{}')
            try:
                new_settings = json.loads(body)
            except Exception:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )

            result = self.settings_service.update_settings(new_settings)
            if not result.get('ok'):
                return HttpResponse(
                    status_code=400,
                    data=result
                )

            return HttpResponse(
                status_code=200,
                data=result
            )
        except Exception as e:
            logger.error("Error in update settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot update settings: " + str(e)
            )

    def handle_reset_settings(self, request):
        """DELETE /settings - сбросить настройки к значениям по умолчанию."""
        try:
            if request.get('method') != 'DELETE':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use DELETE"
                )

            result = self.settings_service.reset_settings()
            status_code = 200 if result.get('ok') else 500
            return HttpResponse(
                status_code=status_code,
                data=result
            )
        except Exception as e:
            logger.error("Error in reset settings: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot reset settings: " + str(e)
            )
