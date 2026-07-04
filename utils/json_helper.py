# utils/json_helper.py
import json

class JSONHelper:
    """Вспомогательный класс для работы с JSON"""
    
    @staticmethod
    def safe_dumps(obj):
        """Безопасная сериализация в JSON"""
        try:
            return json.dumps(obj)
        except:
            return json.dumps({'error': 'JSON serialization failed'})
    
    @staticmethod
    def safe_loads(json_str):
        """Безопасная десериализация из JSON"""
        try:
            return json.loads(json_str)
        except:
            return None
    
    @staticmethod
    def is_valid_json(json_str):
        """Проверка валидности JSON"""
        try:
            json.loads(json_str)
            return True
        except:
            return False