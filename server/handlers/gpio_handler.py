# server/handlers/gpio_handler.py
import machine
import json
from models.response import HttpResponse
from utils.logger import logger

class GPIOHandler:
    """Обработчик эндпоинтов для работы с GPIO"""
    
    def __init__(self, gpio_service):
        self.gpio_service = gpio_service
    
    
    def handle_get_all(self, request):
        """GET /gpio - получить состояние всех пинов с возможностью фильтрации"""
        try:
            # Получаем query параметры
            query = request.get('query', {})
            mode_filter = query.get('mode')
            
            # Получаем все пины и метаданные
            pins_state, meta = self.gpio_service.get_all_pins()
            
            # Если нужно отфильтровать по режиму
            if mode_filter and mode_filter.lower() in ['in', 'out']:
                filtered_pins = {}
                for pin_num, pin in self.gpio_service.pins.items():
                    pin_mode = self.gpio_service.pin_modes.get(pin_num, 'UNKNOWN')
                    if pin_mode.lower() == mode_filter.lower():
                        try:
                            filtered_pins[str(pin_num)] = pin.value()
                        except:
                            filtered_pins[str(pin_num)] = None
                
                pins_state = filtered_pins
                meta = {
                    'total_pins': len(filtered_pins),
                    'message': 'Showing pins in ' + mode_filter + ' mode',
                    'filter': mode_filter
                }
            
            # Добавляем query параметры в метаданные для отладки
            if query:
                meta['query_params'] = query
            
            return HttpResponse(
                status_code=200,
                data={'pins': pins_state, 'meta': meta}
            )
            
        except Exception as e:
            logger.error("Error in GPIO get all: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot read GPIO: " + str(e)
            )

    # server/handlers/gpio_handler.py - улучшенный GET /gpio/:pin
    def handle_get_pin(self, request):
        """GET /gpio/:pin - получить состояние конкретного пина с метаданными"""
        try:
            params = request.get('params', {})
            pin_number = params.get('pin')
            
            if pin_number is None:
                return HttpResponse(
                    status_code=400,
                    error="Missing pin parameter"
                )
            
            try:
                pin_number = int(pin_number)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Pin must be a number"
                )
            
            pin_state = self.gpio_service.get_pin_state(pin_number)
            if pin_state is None:
                return HttpResponse(
                    status_code=404,
                    error="Pin " + str(pin_number) + " not found or cannot be read"
                )
            
            # Получаем режим пина
            pin_mode = self.gpio_service.pin_modes.get(pin_number, 'UNKNOWN')
            
            return HttpResponse(
                status_code=200,
                data={
                    'pin': pin_number,
                    'state': pin_state,
                    'mode': pin_mode,
                    'meta': {
                        'writable': pin_mode == 'OUT',
                        'readable': pin_mode in ['IN', 'OUT']
                    }
                }
            )
        except Exception as e:
            logger.error("Error in GPIO get pin: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot read pin: " + str(e)
            )
        
    def handle_set_pin(self, request):
        """POST /gpio/:pin - установить состояние пина"""
        try:
            # Получаем параметр pin из request
            params = request.get('params', {})
            pin_number = params.get('pin')
            
            if pin_number is None:
                return HttpResponse(
                    status_code=400,
                    error="Missing pin parameter"
                )
            
            # Преобразуем в число
            try:
                pin_number = int(pin_number)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Pin must be a number"
                )
            
            # Парсим тело запроса
            body = request.get('body', '{}')
            
            try:
                data = json.loads(body)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )
            
            state = data.get('state')
            if state is None:
                return HttpResponse(
                    status_code=400,
                    error="Missing 'state' parameter in body"
                )
            
            # Преобразуем state в число (0 или 1)
            try:
                state = int(state)
                if state not in [0, 1]:
                    return HttpResponse(
                        status_code=400,
                        error="State must be 0 or 1"
                    )
            except:
                return HttpResponse(
                    status_code=400,
                    error="State must be a number (0 or 1)"
                )
            
            result = self.gpio_service.set_pin_state(pin_number, state)
            
            if not result:
                return HttpResponse(
                    status_code=500,
                    error="Failed to set pin " + str(pin_number)
                )
            
            return HttpResponse(
                status_code=200,
                data={'pin': pin_number, 'state': state, 'result': 'success'}
            )
        except Exception as e:
            logger.error("Error in GPIO set pin: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot set pin: " + str(e)
            )

    # server/handlers/gpio_handler.py - добавить новый метод
    def handle_batch_set(self, request):
        """POST /gpio/batch - установить состояние нескольких пинов сразу"""
        try:
            if request.get('method') != 'POST':
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use POST"
                )
            
            body = request.get('body', '{}')
            
            try:
                data = json.loads(body)
            except:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )
            
            pins_to_set = data.get('pins', {})
            results = {}
            
            for pin_str, state in pins_to_set.items():
                try:
                    pin = int(pin_str)
                    state_val = int(state)
                    if state_val not in [0, 1]:
                        results[pin_str] = {'success': False, 'error': 'State must be 0 or 1'}
                    else:
                        success = self.gpio_service.set_pin_state(pin, state_val)
                        results[pin_str] = {'success': success}
                except:
                    results[pin_str] = {'success': False, 'error': 'Invalid pin or state'}
            
            return HttpResponse(
                status_code=200,
                data={'results': results, 'meta': {'total': len(results)}}
            )
        except Exception as e:
            logger.error("Error in GPIO batch set: " + str(e))
            return HttpResponse(
                status_code=500,
                error="Cannot set pins: " + str(e)
            )   