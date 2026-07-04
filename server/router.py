# server/router.py
import re

class Router:
    """Класс для управления маршрутами с учетом HTTP методов"""
    
    def __init__(self):
        # Храним обработчики в формате {method:path: handler}
        self.routes = {}  # {method+path: handler}
        self.dynamic_routes = []  # [(method, pattern, handler, param_names)]
    
    def route(self, path, methods=['GET']):
        """
        Декоратор для добавления маршрута с указанием HTTP методов
        Использование:
            @router.route('/info', methods=['GET'])
            def handle_info(request):
                ...
        """
        def decorator(handler):
            for method in methods:
                self._add_route(method, path, handler)
            return handler
        return decorator
    
    def add_route(self, method, path, handler):
        """Добавление маршрута вручную"""
        self._add_route(method, path, handler)
    
    def _add_route(self, method, path, handler):
        """Внутренний метод добавления маршрута"""
        method = method.upper()
        
        if ':' in path:
            # Динамический маршрут
            # Извлекаем имена параметров
            param_names = []
            pattern_str = path
            
            # Находим все параметры вида :param
            # Используем простой поиск без re для совместимости
            import re as regex
            param_pattern = regex.compile(r':([a-zA-Z_][a-zA-Z0-9_]*)')
            
            def replacer(match):
                param_names.append(match.group(1))
                return '([^/]+)'
            
            pattern_str = param_pattern.sub(replacer, pattern_str)
            pattern = regex.compile('^' + pattern_str + '$')
            
            self.dynamic_routes.append((method, pattern, handler, param_names))
        else:
            # Статический маршрут - используем ключ method+path
            key = method + ':' + path
            self.routes[key] = handler
    
    def dispatch(self, request):
        """Вызов обработчика для пути и метода"""
        if not request:
            return None
            
        path = request.get('path', '')
        method = request.get('method', '').upper()
        
        # Проверяем статические маршруты
        static_key = method + ':' + path
        if static_key in self.routes:
            handler = self.routes[static_key]
            return handler(request)
        
        # Проверяем динамические маршруты
        for route_method, pattern, handler, param_names in self.dynamic_routes:
            if route_method == method:
                match = pattern.match(path)
                if match:
                    # Извлекаем параметры из пути
                    params = {}
                    for i, param_name in enumerate(param_names):
                        params[param_name] = match.group(i + 1)
                    
                    # Добавляем параметры в запрос
                    request['params'] = params
                    
                    # Вызываем обработчик
                    return handler(request)
        
        return None  # Маршрут не найден