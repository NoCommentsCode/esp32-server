# services/storage_service.py
import json
import os

class StorageService:
    """Сервис для работы с хранением данных"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_settings = {
            'wifi': {
                'ssid': '',
                'password': ''
            },
            'server': {
                'port': 80,
                'debug': True
            },
            'sensors': {
                'read_interval': 5,
                'enabled': True
            }
        }
    
    def get_settings(self):
        """Получить настройки из файла"""
        try:
            if self._file_exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                return settings
            else:
                return self.default_settings
        except:
            return self.default_settings
    
    def update_settings(self, new_settings):
        """Обновить настройки"""
        try:
            # Загружаем текущие настройки
            current = self.get_settings()
            
            # Рекурсивно обновляем
            self._deep_update(current, new_settings)
            
            # Сохраняем
            with open(self.config_file, 'w') as f:
                json.dump(current, f)
            
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def reset_settings(self):
        """Сбросить настройки до дефолтных"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.default_settings, f)
            return True
        except:
            return False
    
    def _deep_update(self, target, source):
        """Рекурсивное обновление словаря"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _file_exists(self, filename):
        """Проверка существования файла"""
        try:
            os.stat(filename)
            return True
        except:
            return False