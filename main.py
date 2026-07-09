# main.py
import gc
from config import Config
from wifi_manager import WiFiManager
from utils.logger import logger

# Импортируем компоненты сервера
from server.app import ESP32Server
from server.router import Router

# Импортируем обработчики
from server.handlers.info_handler import InfoHandler
from server.handlers.discovery_handler import DiscoveryHandler
from server.handlers.sensors_handler import SensorsHandler
from server.handlers.gpio_handler import GPIOHandler
from server.handlers.settings_handler import SettingsHandler
from server.handlers.system_handler import SystemHandler
from server.handlers.dht_handler import DHTHandler
from server.handlers.weather_handler import WeatherHandler
from server.handlers.bmp280_handler import BMP280Handler
from server.handlers.co2_handler import CO2Handler

# Импортируем сервисы
from services.device_service import DeviceService
from services.sensor_service import SensorService
from services.gpio_service import GPIOService
from services.settings_service import SettingsService
from services.dht_service import DHTService
from services.weather_service import WeatherService
from services.bmp280_service import BMP280Service
from services.co2_service import CO2Service
from services.display_service import DisplayService
from services.sensor_polling_service import SensorPollingService

def register_routes(router, services):
    """Регистрация всех маршрутов"""
    
    # Создаем экземпляры обработчиков
    info_handler = InfoHandler(services['device'])
    discovery_handler = DiscoveryHandler(services['device'])
    sensors_handler = SensorsHandler(services['sensors'])
    gpio_handler = GPIOHandler(services['gpio'])
    settings_handler = SettingsHandler(services['settings'])
    system_handler = SystemHandler(services['wifi_manager'])
    dht_handler = DHTHandler(services['dht'])
    weather_handler = WeatherHandler(services['weather'])
    bmp280_handler = BMP280Handler(services['bmp280'])
    co2_handler = CO2Handler(services['co2'])
    
    # Регистрируем маршруты с указанием HTTP методов
    
    # GET /discovery - идентификация станции в сети
    router.route('/discovery', methods=['GET'])(discovery_handler.handle)

    # GET /info - информация об устройстве
    router.route('/info', methods=['GET'])(info_handler.handle)
    
    # GET /sensors - получить данные датчиков
    router.route('/sensors', methods=['GET'])(sensors_handler.handle_get)
    
    # POST /sensors - изменить настройки датчиков
    router.route('/sensors', methods=['POST'])(sensors_handler.handle_post)
    
    # GET /gpio - получить состояние всех пинов
    router.route('/gpio', methods=['GET'])(gpio_handler.handle_get_all)
    
    # GET /gpio/:pin - получить состояние конкретного пина
    router.route('/gpio/:pin', methods=['GET'])(gpio_handler.handle_get_pin)
    
    # POST /gpio/:pin - установить состояние пина
    router.route('/gpio/:pin', methods=['POST'])(gpio_handler.handle_set_pin)
    
    # GET /settings - получить настройки
    router.route('/settings', methods=['GET'])(settings_handler.handle_get_settings)
    
    # POST /settings - обновить настройки
    router.route('/settings', methods=['POST'])(settings_handler.handle_update_settings)
    
    # DELETE /settings - сбросить настройки
    router.route('/settings', methods=['DELETE'])(settings_handler.handle_reset_settings)
    
    # GET /health - проверка работоспособности
    router.route('/health', methods=['GET'])(system_handler.handle_health)
    
    # POST /system/restart - перезагрузка
    router.route('/system/restart', methods=['POST'])(system_handler.handle_restart)
    
    # GET /info/deep - расширенная информация
    router.route('/info/deep', methods=['GET'])(system_handler.handle_info_deep)

    # POST /gpio/batch - установить несколько пинов одновременно
    router.route('/gpio/batch', methods=['POST'])(gpio_handler.handle_batch_set)

    # GET /sensor/dht - получить показания датчика
    router.route('/sensor/dht', methods=['GET'])(dht_handler.handle_get_sensor)
    
    # GET /sensor/dht/status - получить статус датчика
    router.route('/sensor/dht/status', methods=['GET'])(dht_handler.handle_get_status)

    # GET /sensor/bmp280 - получить показания BMP280
    router.route('/sensor/bmp280', methods=['GET'])(bmp280_handler.handle_get_sensor)

    # GET /sensor/bmp280/status - получить статус BMP280
    router.route('/sensor/bmp280/status', methods=['GET'])(bmp280_handler.handle_get_status)

    # GET /sensor/co2 - получить концентрацию CO2
    router.route('/sensor/co2', methods=['GET'])(co2_handler.handle_get_sensor)
    router.route('/sensor/co2/status', methods=['GET'])(co2_handler.handle_get_status)
    router.route('/sensor/co2/probe', methods=['GET'])(co2_handler.handle_probe)
    router.route('/sensor/co2/abc', methods=['POST'])(co2_handler.handle_set_abc)

    # Алиасы для обратной совместимости
    router.route('/sensor/mhz19c', methods=['GET'])(co2_handler.handle_get_sensor)
    router.route('/sensor/mhz19c/status', methods=['GET'])(co2_handler.handle_get_status)
    router.route('/sensor/mhz19c/probe', methods=['GET'])(co2_handler.handle_probe)
    router.route('/sensor/mhz19c/abc', methods=['POST'])(co2_handler.handle_set_abc)

    # GET /weather - получить погоду (с опциональным ?force=true)
    router.route('/weather', methods=['GET'])(weather_handler.handle_get_weather)
    
    # POST /weather/refresh - принудительно обновить погоду
    router.route('/weather/refresh', methods=['POST'])(weather_handler.handle_refresh_weather)
    
    # Выводим информацию о зарегистрированных маршрутах
    logger.info("Registered static routes:")
    for key in router.routes:
        logger.info("  " + key)
    
    logger.info("Registered dynamic routes:")
    for route in router.dynamic_routes:
        # В MicroPython нет атрибута pattern, просто выводим метод
        method = route[0]
        logger.info("  " + method + " (dynamic route)")

def main():
    """Основная функция"""
    logger.info("=" * 50)
    logger.info("ESP32 REST API Server Starting...")
    logger.info("=" * 50)

    gc.collect()

    # Wi-Fi инициализируется до чтения config.json — на ESP32 нужна свободная память.
    wifi_manager = WiFiManager()
    if not wifi_manager.connect():
        logger.error("Failed to connect to Wi-Fi")
        return

    Config.load_from_file()
    
    # 1. Инициализация сервисов (датчики до GPIO — UART/I2C пины не должны захватываться как IN)
    services = {
        'device': DeviceService(wifi_manager),
        'sensors': SensorService(),
        'wifi_manager': wifi_manager,
        'dht': DHTService(pin_number=Config.DHT_PIN) if Config.DHT_ENABLED else None,
        'weather': WeatherService() if Config.WEATHER_ENABLED else None,
        'bmp280': BMP280Service(
            i2c_id=Config.BMP280_I2C_ID,
            scl_pin=Config.BMP280_SCL_PIN,
            sda_pin=Config.BMP280_SDA_PIN,
            address=Config.BMP280_ADDRESS,
            i2c_freq=Config.BMP280_I2C_FREQ
        ) if Config.BMP280_ENABLED else None,
        'co2': CO2Service(
            sensor_type=Config.CO2_SENSOR_TYPE,
            uart_id=Config.CO2_UART_ID,
            tx_pin=Config.CO2_TX_PIN,
            rx_pin=Config.CO2_RX_PIN,
            baudrate=Config.CO2_BAUDRATE,
            swap_tx_rx=Config.CO2_SWAP_TX_RX,
            c8_mode=Config.CO2_C8_MODE
        ) if Config.CO2_ENABLED else None,
        'gpio': GPIOService(),
    }

    if Config.DISPLAY_ENABLED:
        services['display'] = DisplayService(
            i2c_id=Config.DISPLAY_I2C_ID,
            sda_pin=Config.DISPLAY_SDA_PIN,
            scl_pin=Config.DISPLAY_SCL_PIN,
            i2c_freq=Config.DISPLAY_I2C_FREQ,
            width=Config.DISPLAY_WIDTH,
            height=Config.DISPLAY_HEIGHT,
            address=Config.DISPLAY_ADDRESS,
            color_split_y=Config.DISPLAY_COLOR_SPLIT_Y,
            event_duration_ms=Config.DISPLAY_EVENT_DURATION_MS,
            idle_refresh_ms=Config.DISPLAY_IDLE_REFRESH_MS,
            wifi_manager=wifi_manager,
            dht_service=services['dht'],
            bmp280_service=services['bmp280'],
            co2_service=services['co2']
        )
    else:
        services['display'] = None

    has_pollable_sensors = Config.has_pollable_sensors()
    services['sensor_poll'] = SensorPollingService(
        dht_service=services['dht'],
        bmp280_service=services['bmp280'],
        co2_service=services['co2'],
        interval_ms=Config.SENSOR_POLL_INTERVAL_MS,
        enabled=Config.SENSOR_POLL_ENABLED and has_pollable_sensors
    )

    services['settings'] = SettingsService(services)
    
    # 3. Инициализация маршрутизатора
    router = Router()
    
    # 4. Регистрация маршрутов
    register_routes(router, services)
    
    server = ESP32Server(
        wifi_manager,
        router,
        services.get('display'),
        services.get('sensor_poll')
    )

    if server.start():
        try:
            server.run()
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        except Exception as e:
            logger.error("Critical error: " + str(e))
        finally:
            server.stop()
    else:
        logger.error("Failed to start server")

# Точка входа
if __name__ == '__main__':
    main()