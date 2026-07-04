# models/response.py
import json

class HttpResponse:
    """Стандартизированный HTTP ответ"""
    
    def __init__(self, status_code=200, data=None, error=None):
        self.status_code = status_code
        self.data = data
        self.error = error
    
    def to_bytes(self):
        """Конвертация в байты для отправки"""
        # Формируем тело ответа
        if self.error:
            body = json.dumps({'error': self.error})
        else:
            body = json.dumps(self.data) if self.data else '{}'
        
        # Формируем заголовки
        headers = f"HTTP/1.1 {self.status_code} {self._get_status_text()}\r\n"
        headers += "Content-Type: application/json; charset=utf-8\r\n"
        headers += "Connection: close\r\n"
        headers += f"Content-Length: {len(body.encode('utf-8'))}\r\n"  # Важно: длина в байтах!
        headers += "\r\n"
        
        # Объединяем заголовки и тело
        response = headers + body
        
        # Возвращаем как байты
        return response.encode('utf-8')
    
    def _get_status_text(self):
        """Получение текстового описания статуса"""
        status_texts = {
            200: 'OK',
            400: 'Bad Request',
            404: 'Not Found',
            405: 'Method Not Allowed',
            500: 'Internal Server Error',
            503: 'Service Unavailable'
        }
        return status_texts.get(self.status_code, 'Unknown')