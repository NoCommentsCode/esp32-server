# server/handlers/system_handler.py
import machine
import time
from models.response import HttpResponse

class SystemHandler:
    """Обработчик системных эндпоинтов"""
    
    def __init__(self, wifi_manager):
        self.wifi_manager = wifi_manager
    
    def handle_health(self, request_data):
        """GET /health - проверка работоспособности"""
        return HttpResponse(
            status_code=200,
            data={
                'status': 'OK',
                'uptime': self._get_uptime(),
                'memory_free': self._get_memory_free()
            }
        )
    
    def handle_restart(self, request_data):
        """POST /system/restart - перезагрузка устройства"""
        try:
            # Отправляем ответ перед перезагрузкой
            response = HttpResponse(
                status_code=200,
                data={'message': 'System restarting in 1 second...'}
            )
            
            # Перезагружаемся через 1 секунду
            time.sleep(1)
            machine.reset()
            
            return response
        except Exception as e:
            return HttpResponse(
                status_code=500,
                error=f"Cannot restart: {str(e)}"
            )
    
    def handle_info_deep(self, request_data):
        """GET /info/deep - расширенная информация"""
        try:
            info = {
                'wifi': self.wifi_manager.get_status(),
                'reset_cause': machine.reset_cause(),
                'wake_reason': machine.wake_reason(),
                'unique_id': machine.unique_id().hex(),
                'freq': machine.freq(),
                'time': time.localtime()
            }
            return HttpResponse(
                status_code=200,
                data=info
            )
        except Exception as e:
            return HttpResponse(
                status_code=500,
                error=f"Cannot get deep info: {str(e)}"
            )
    
    def _get_uptime(self):
        """Получение времени работы (упрощенно)"""
        # В реальном проекте нужно хранить время старта
        return 0
    
    def _get_memory_free(self):
        """Получение свободной памяти"""
        import gc
        return gc.mem_free()