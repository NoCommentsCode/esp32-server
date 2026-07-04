# services/gpio_service.py (расширенная версия)
import machine

class GPIOService:
    """Сервис для работы с GPIO"""
    
    def __init__(self):
        self.pins = {}
        self.pin_modes = {}  # Храним режим каждого пина
        self._init_default_pins()  # Инициализируем пины по умолчанию
    
    def _init_default_pins(self):
        """Инициализация пинов по умолчанию"""
        # Список доступных пинов на ESP32
        # Включаем наиболее часто используемые пины
        available_pins = [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33]
        
        for pin_num in available_pins:
            try:
                # Пробуем инициализировать как INPUT с подтяжкой вниз
                self.pins[pin_num] = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_DOWN)
                self.pin_modes[pin_num] = 'IN'
            except Exception as e:
                # Если пин недоступен, просто пропускаем
                # Некоторые пины могут быть заняты (например, 6-11 зарезервированы для SPI flash)
                pass

    def get_all_pins(self):
        """Получить состояние всех инициализированных пинов"""
        result = {}
        pin_modes = {}
        
        for pin_num, pin in self.pins.items():
            try:
                result[str(pin_num)] = pin.value()
                pin_modes[str(pin_num)] = self.pin_modes.get(pin_num, 'UNKNOWN')
            except:
                result[str(pin_num)] = None
                pin_modes[str(pin_num)] = 'ERROR'
        
        # Добавляем расширенную метаинформацию
        meta = {
            'total_pins': len(self.pins),
            'message': 'Showing initialized pins',
            'modes': pin_modes,  # Режим каждого пина
            'available_pins': list(self.pins.keys())  # Список доступных пинов
        }
        
        return result, meta
    
    def get_all_available_pins(self):
        """Получить состояние всех доступных пинов (создавая их при необходимости)"""
        result = {}
        
        # Список всех возможных пинов ESP32
        all_possible_pins = range(0, 40)  # ESP32 имеет пины 0-39
        
        for pin_num in all_possible_pins:
            try:
                # Пробуем прочитать пин
                # Создаем временный пин для чтения
                pin = machine.Pin(pin_num, machine.Pin.IN)
                result[str(pin_num)] = pin.value()
                # Сохраняем в словарь для последующего использования
                if pin_num not in self.pins:
                    self.pins[pin_num] = pin
                    self.pin_modes[pin_num] = 'IN'
            except:
                # Пин недоступен или не существует
                pass
        
        return result
    
    def get_pin_state(self, pin_number):
        """Получить состояние конкретного пина"""
        # Если пин еще не инициализирован, пробуем инициализировать как INPUT
        if pin_number not in self.pins:
            try:
                self.pins[pin_number] = machine.Pin(pin_number, machine.Pin.IN)
                self.pin_modes[pin_number] = 'IN'
            except:
                return None
        
        try:
            return self.pins[pin_number].value()
        except:
            return None
    
    def set_pin_state(self, pin_number, state):
        """Установить состояние пина"""
        # Проверяем, можно ли использовать этот пин как OUTPUT
        # Некоторые пины нельзя использовать как OUTPUT (например, входные только)
        forbidden_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        # 0, 2, 4, 5, 12, 13, 14, 15 - часто используются, но могут быть OUTPUT
        
        # Если пин еще не инициализирован или не в режиме OUTPUT
        if pin_number not in self.pins or self.pin_modes.get(pin_number) != 'OUT':
            try:
                self.pins[pin_number] = machine.Pin(pin_number, machine.Pin.OUT)
                self.pin_modes[pin_number] = 'OUT'
            except Exception as e:
                return False
        
        try:
            self.pins[pin_number].value(state)
            return True
        except:
            return False
    
    def add_pin(self, pin_number, mode='IN', pull=None):
        """Добавить новый пин в сервис"""
        try:
            if mode == 'IN':
                if pull == 'UP':
                    pin = machine.Pin(pin_number, machine.Pin.IN, machine.Pin.PULL_UP)
                elif pull == 'DOWN':
                    pin = machine.Pin(pin_number, machine.Pin.IN, machine.Pin.PULL_DOWN)
                else:
                    pin = machine.Pin(pin_number, machine.Pin.IN)
            elif mode == 'OUT':
                pin = machine.Pin(pin_number, machine.Pin.OUT)
            else:
                return False
            
            self.pins[pin_number] = pin
            self.pin_modes[pin_number] = mode
            return True
        except:
            return False