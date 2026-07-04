# utils/validators.py
import re

class Validators:
    """Класс для валидации данных"""
    
    @staticmethod
    def validate_ip(ip):
        """Проверка IP адреса"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(pattern, ip):
            parts = ip.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        return False
    
    @staticmethod
    def validate_port(port):
        """Проверка порта"""
        try:
            port = int(port)
            return 1 <= port <= 65535
        except:
            return False
    
    @staticmethod
    def validate_pin(pin):
        """Проверка номера пина"""
        try:
            pin = int(pin)
            valid_pins = [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23]
            return pin in valid_pins
        except:
            return False
    
    @staticmethod
    def validate_ssid(ssid):
        """Проверка SSID"""
        if not ssid:
            return False
        return 1 <= len(ssid) <= 32
    
    @staticmethod
    def validate_password(password):
        """Проверка пароля"""
        if password is None:
            return False
        return 0 <= len(password) <= 64  # Пустой пароль разрешен