# server/app.py
import socket
import json
from config import Config
from utils.logger import logger
from models.response import HttpResponse

class ESP32Server:
    """Основной класс сервера"""
    
    def __init__(self, wifi_manager, router):
        self.wifi_manager = wifi_manager
        self.router = router
        # Временно отключено: self.display_service = display_service
        self.server_socket = None
        self.is_running = False
    
    def start(self):
        """Запуск сервера"""
        if not self.wifi_manager.is_connected:
            logger.error("Wi-Fi not connected")
            return False
        
        try:
            # Создаем сокет
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Увеличиваем буфер отправки (если доступно)
            try:
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
            except:
                pass  # Не все версии MicroPython поддерживают это
            
            self.server_socket.bind((Config.SERVER_HOST, Config.SERVER_PORT))
            self.server_socket.listen(Config.SERVER_MAX_CLIENTS)
            
            self.is_running = True
            logger.info("Server started on http://" + self.wifi_manager.get_ip() + ":" + str(Config.SERVER_PORT))
            
            return True
        except Exception as e:
            logger.error("Error starting server: " + str(e))
            return False
    
    def run(self):
        """Основной цикл обработки запросов"""
        while self.is_running:
            try:
                client_sock, client_addr = self.server_socket.accept()
                logger.debug("Connection from " + client_addr[0])
                
                self._handle_client(client_sock)
            except Exception as e:
                logger.error("Error in main loop: " + str(e))

    def _handle_client(self, client_sock):
        """Обработка одного клиента"""
        try:
            # Получаем данные
            request_data = client_sock.recv(Config.SERVER_BUFFER_SIZE)
            
            if not request_data:
                return
            
            # Парсим запрос
            request = self._parse_request(request_data)
            
            if request:
                # Маршрутизируем
                response = self.router.dispatch(request)
                
                # Отправляем ответ
                if response:
                    response_bytes = response.to_bytes()
                    # Используем sendall для гарантированной отправки всех данных
                    client_sock.sendall(response_bytes)
                    logger.debug(f"Sent {len(response_bytes)} bytes")
                else:
                    # 404 Not Found
                    response = HttpResponse(status_code=404, error="Not found")
                    response_bytes = response.to_bytes()
                    client_sock.sendall(response_bytes)
            else:
                # Не удалось распарсить запрос
                response = HttpResponse(status_code=400, error="Bad request")
                response_bytes = response.to_bytes()
                client_sock.sendall(response_bytes)
                
        except Exception as e:
            logger.error("Error handling request: " + str(e))
        finally:
            client_sock.close()
    
    def _parse_request(self, data):
        """Парсинг HTTP запроса с поддержкой query параметров"""
        try:
            request_str = data.decode()
            lines = request_str.split('\r\n')
            
            if not lines:
                return None
            
            # Парсим первую строку (метод, путь, версия)
            first_line = lines[0].split()
            if len(first_line) < 2:
                return None
                
            method = first_line[0]
            full_path = first_line[1]  # Может содержать query параметры
            version = first_line[2] if len(first_line) > 2 else 'HTTP/1.1'
            
            # Разделяем путь и query параметры
            path = full_path
            query_params = {}
            
            if '?' in full_path:
                path, query_string = full_path.split('?', 1)
                # Парсим query параметры
                if query_string:
                    for param in query_string.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            query_params[key] = value
                        else:
                            query_params[param] = ''
            
            # Парсим заголовки
            headers = {}
            body = None
            body_started = False
            body_lines = []
            
            for line in lines[1:]:
                if not body_started:
                    if line == '':
                        body_started = True
                    else:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip()] = value.strip()
                else:
                    body_lines.append(line)
            
            if body_lines:
                body = '\n'.join(body_lines)
            
            return {
                'method': method,
                'path': path,  # Путь без query параметров
                'full_path': full_path,  # Полный путь с параметрами
                'query': query_params,  # Разобранные query параметры
                'version': version,
                'headers': headers,
                'body': body,
                'raw': request_str
            }
            
        except Exception as e:
            logger.error("Error parsing request: " + str(e))
            return None
    
    def stop(self):
        """Остановка сервера"""
        if self.server_socket:
            self.server_socket.close()
        self.is_running = False
        logger.info("Server stopped")