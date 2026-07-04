# config.py
import json
import os

class Config:
    """Класс для хранения конфигурации приложения"""
    
    # Wi-Fi настройки
    WIFI_SSID = 'your_ssid'
    WIFI_PASSWORD = 'your_password'
    
    # Серверные настройки
    SERVER_PORT = 80
    SERVER_HOST = '0.0.0.0'
    SERVER_MAX_CLIENTS = 5
    SERVER_BUFFER_SIZE = 1024

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

    # SPI TFT (GMT147SPI / ST7789) настройки
    # Временно отключено. Оставлено для быстрого возврата функционала.
    # DISPLAY_ENABLED = True
    # DISPLAY_SPI_ID = 1
    # DISPLAY_SCK_PIN = 18
    # DISPLAY_MOSI_PIN = 23
    # DISPLAY_MISO_PIN = None
    # DISPLAY_BAUDRATE = 40000000
    # DISPLAY_MIN_BAUDRATE = 5000000
    # DISPLAY_USE_SOFT_SPI_FALLBACK = True
    # DISPLAY_SPI_POLARITY = 0
    # DISPLAY_SPI_PHASE = 0
    # DISPLAY_WIDTH = 172
    # DISPLAY_HEIGHT = 320
    # DISPLAY_ROTATION = 1
    # DISPLAY_CS_PIN = 5
    # DISPLAY_DC_PIN = 2
    # DISPLAY_RST_PIN = 4
    # DISPLAY_BL_PIN = 15
    # DISPLAY_BL_ACTIVE_HIGH = True
    # DISPLAY_USE_BL_PWM = False
    # DISPLAY_BL_PWM_FREQ = 1000
    # DISPLAY_EVENT_DURATION_MS = 2000

    # WeatherAPI настройки
    WEATHER_API_KEY = 'e0eb9a03e7954f99b0f180048262903'
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
            'WIFI_SSID': cls.WIFI_SSID,
            'WIFI_PASSWORD': cls.WIFI_PASSWORD,
            'SERVER_PORT': cls.SERVER_PORT,
            'DEBUG': cls.DEBUG,
            'API_KEY': cls.API_KEY
        }
        try:
            with open(filename, 'w') as f:
                json.dump(config_data, f)
        except:
            pass