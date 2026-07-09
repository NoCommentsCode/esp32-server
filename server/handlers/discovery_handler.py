# server/handlers/discovery_handler.py
from models.response import HttpResponse
from utils.logger import logger


class DiscoveryHandler:
    """Обработчик эндпоинта /discovery"""

    def __init__(self, device_service):
        self.device_service = device_service

    def handle(self, request):
        """Обработка GET /discovery"""
        try:
            if request.get('method') != 'GET':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            return HttpResponse(
                status_code=200,
                data=self.device_service.get_discovery_info()
            )
        except Exception as e:
            logger.error("Error in discovery handler: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: " + str(e)
            )
