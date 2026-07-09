# config.py
import json

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD, WEATHER_API_KEY
except ImportError:
    WIFI_SSID = ''
    WIFI_PASSWORD = ''
    WEATHER_API_KEY = ''


class Config:
    """Класс для хранения конфигурации приложения"""

    # Wi-Fi (из secrets.py / .env)
    WIFI_SSID = WIFI_SSID
    WIFI_PASSWORD = WIFI_PASSWORD

    # Серверные настройки
    SERVER_PORT = 80
    SERVER_HOST = '0.0.0.0'
    SERVER_MAX_CLIENTS = 5
    SERVER_BUFFER_SIZE = 1024

    # Включение модулей (разная аппаратная конфигурация станций)
    DHT_ENABLED = True
    DHT_PIN = 14
    BMP280_ENABLED = True
    CO2_ENABLED = True
    WEATHER_ENABLED = True

    # BMP280 настройки
    BMP280_I2C_ID = 0
    BMP280_SCL_PIN = 22
    BMP280_SDA_PIN = 21
    BMP280_ADDRESS = 0x76
    BMP280_I2C_FREQ = 100000

    # CO2 датчик (C8 или MH-Z19C) — UART, pin-compatible
    CO2_SENSOR_TYPE = 'c8'      # 'c8' или 'mhz19c'
    CO2_UART_ID = 2
    CO2_TX_PIN = 17             # ESP32 TX -> датчик Rx
    CO2_RX_PIN = 16             # ESP32 RX <- датчик Tx
    CO2_BAUDRATE = 9600
    CO2_SWAP_TX_RX = False
    CO2_C8_MODE = 'active'      # 'active' (1 с) или 'query' (по запросу)

    # I2C OLED (GMO09605 / SSD1306, 128x64, двухцветный)
    DISPLAY_ENABLED = True
    DISPLAY_I2C_ID = 0
    DISPLAY_SDA_PIN = 21
    DISPLAY_SCL_PIN = 22
    DISPLAY_I2C_FREQ = 400000
    DISPLAY_WIDTH = 128
    DISPLAY_HEIGHT = 64
    DISPLAY_ADDRESS = 0x3C
    DISPLAY_COLOR_SPLIT_Y = 16
    DISPLAY_EVENT_DURATION_MS = 2000
    DISPLAY_IDLE_REFRESH_MS = 3000

    # Фоновый опрос датчиков (не по HTTP)
    SENSOR_POLL_ENABLED = True
    SENSOR_POLL_INTERVAL_MS = 5000

    # Идентификация станции (discovery, будущий агрегатор)
    STATION_ID = 'station-01'
    STATION_NAME = 'Метеостанция'
    API_VERSION = '2.0'
    DEVICE_TYPE = 'esp32_weather_station'

    # WeatherAPI настройки
    WEATHER_API_KEY = WEATHER_API_KEY
    WEATHER_CITY = 'Moscow'
    WEATHER_LANG = 'ru'
    WEATHER_UPDATE_INTERVAL = 600  # Обновлять каждые 10 минут (в секундах)

    # Таймауты
    WIFI_TIMEOUT = 10
    REQUEST_TIMEOUT = 5
    WEATHER_API_TIMEOUT = 10  # Таймаут для запросов к WeatherAPI

    # Режим отладки
    DEBUG = True

    @classmethod
    def get_capabilities(cls):
        """Список возможностей станции для /discovery."""
        capabilities = []
        if cls.DHT_ENABLED:
            capabilities.append('dht')
        if cls.BMP280_ENABLED:
            capabilities.append('bmp280')
        if cls.CO2_ENABLED:
            capabilities.append('co2')
        if cls.WEATHER_ENABLED and cls.WEATHER_API_KEY:
            capabilities.append('weather')
        return capabilities

    @classmethod
    def load_from_file(cls, filename='config.json'):
        """Загрузка конфигурации из JSON файла"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
        except:
            pass

    @classmethod
    def save_to_file(cls, filename='config.json'):
        """Сохранение конфигурации в JSON файл"""
        config_data = {
            'SERVER_PORT': cls.SERVER_PORT,
            'DEBUG': cls.DEBUG,
        }
        try:
            with open(filename, 'w') as f:
                json.dump(config_data, f)
        except:
            pass
