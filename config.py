# config.py
import gc
import json

try:
    from secrets import WIFI_SSID, WIFI_PASSWORD, WEATHER_API_KEY
except ImportError:
    WIFI_SSID = ''
    WIFI_PASSWORD = ''
    WEATHER_API_KEY = ''


class Config:
    """Класс для хранения конфигурации приложения"""

    CONFIG_FILE = '/config.json'
    CONFIG_FILE_CANDIDATES = ('/config.json', 'config.json')

    # Заполняется при load_from_file() — для отладки через /settings meta
    _config_file_path = None
    _config_loaded_keys = []

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
    def has_pollable_sensors(cls):
        """Есть ли датчики для фонового опроса."""
        return cls.DHT_ENABLED or cls.BMP280_ENABLED or cls.CO2_ENABLED

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
    def get_mutable_settings(cls):
        """Текущие значения настроек, доступных через /settings."""
        return {key: getattr(cls, key) for key in MUTABLE_SETTINGS}

    @classmethod
    def get_settings_meta(cls):
        """Метаданные для API настроек."""
        runtime_keys = []
        restart_required_keys = []
        for key, spec in MUTABLE_SETTINGS.items():
            if spec.get('runtime'):
                runtime_keys.append(key)
            else:
                restart_required_keys.append(key)
        return {
            'runtime_keys': runtime_keys,
            'restart_required_keys': restart_required_keys,
            'config_file': cls._config_file_path,
            'config_loaded_keys': list(cls._config_loaded_keys),
        }

    @classmethod
    def coerce_setting(cls, key, value):
        """
        Приводит значение к нужному типу.
        Returns: (coerced_value, error_message)
        """
        if key not in MUTABLE_SETTINGS:
            return None, 'Unknown or read-only setting'

        spec = MUTABLE_SETTINGS[key]
        expected_type = spec['type']

        try:
            if expected_type is bool:
                if isinstance(value, bool):
                    coerced = value
                elif isinstance(value, int) and value in (0, 1):
                    coerced = bool(value)
                elif isinstance(value, str):
                    lowered = value.lower()
                    if lowered in ('true', '1', 'yes', 'on'):
                        coerced = True
                    elif lowered in ('false', '0', 'no', 'off'):
                        coerced = False
                    else:
                        return None, 'Expected boolean'
                else:
                    return None, 'Expected boolean'
            elif expected_type is int:
                coerced = int(value)
            elif expected_type is str:
                coerced = str(value)
            else:
                return None, 'Unsupported setting type'
        except (TypeError, ValueError):
            return None, 'Invalid value type'

        if expected_type is str:
            max_len = spec.get('max_len')
            if max_len and len(coerced) > max_len:
                return None, 'Value too long (max {})'.format(max_len)
            min_len = spec.get('min_len', 0)
            if len(coerced) < min_len:
                return None, 'Value too short (min {})'.format(min_len)

        if expected_type is int:
            min_value = spec.get('min')
            max_value = spec.get('max')
            if min_value is not None and coerced < min_value:
                return None, 'Value must be >= {}'.format(min_value)
            if max_value is not None and coerced > max_value:
                return None, 'Value must be <= {}'.format(max_value)

        allowed = spec.get('allowed')
        if allowed is not None and coerced not in allowed:
            return None, 'Allowed values: {}'.format(', '.join(allowed))

        return coerced, None

    @classmethod
    def _log_config(cls, level, message):
        print('[config] {}: {}'.format(level.upper(), message))

    @classmethod
    def _parse_json_text(cls, text):
        text = text.strip()
        if not text:
            raise ValueError('empty config file')

        try:
            return json.loads(text)
        except Exception:
            pass

        # Hand-edited files sometimes contain Python literals.
        repaired = (
            text.replace('True', 'true')
            .replace('False', 'false')
            .replace('None', 'null')
        )
        return json.loads(repaired)

    @classmethod
    def _quarantine_corrupt_file(cls, path):
        try:
            import os
            bad_path = path + '.bad'
            try:
                os.remove(bad_path)
            except OSError:
                pass
            os.rename(path, bad_path)
            cls._log_config('warning', 'Quarantined corrupt config as {}'.format(bad_path))
        except Exception as e:
            cls._log_config('error', 'Failed to quarantine {}: {}'.format(path, e))

    @classmethod
    def _read_config_file(cls, path):
        with open(path, 'r') as f:
            text = f.read(8192)
        return cls._parse_json_text(text)

    @classmethod
    def _normalize_config_data(cls, data):
        """Плоский формат /settings или legacy nested config.json."""
        if not isinstance(data, dict):
            return {}

        if any(key in MUTABLE_SETTINGS for key in data):
            return data

        flat = {}
        server = data.get('server')
        if isinstance(server, dict):
            if 'port' in server:
                flat['SERVER_PORT'] = server['port']
            if 'debug' in server:
                flat['DEBUG'] = server['debug']

        sensors = data.get('sensors')
        if isinstance(sensors, dict):
            if 'enabled' in sensors:
                flat['SENSOR_POLL_ENABLED'] = sensors['enabled']
            if 'read_interval' in sensors:
                flat['SENSOR_POLL_INTERVAL_MS'] = int(sensors['read_interval']) * 1000

        return flat

    @classmethod
    def _apply_config_data(cls, data):
        loaded = []
        for key, value in data.items():
            if key not in MUTABLE_SETTINGS:
                continue
            coerced, error = cls.coerce_setting(key, value)
            if error is None:
                setattr(cls, key, coerced)
                loaded.append(key)
            else:
                cls._log_config('warning', 'Skip {}: {}'.format(key, error))
        cls._config_loaded_keys = loaded
        return loaded

    @classmethod
    def load_from_file(cls, filename=None):
        """Загрузка изменяемых настроек из JSON перед стартом сервисов."""
        cls._config_file_path = None
        cls._config_loaded_keys = []

        candidates = (filename,) if filename else cls.CONFIG_FILE_CANDIDATES
        seen_paths = set()
        for path in candidates:
            if path in seen_paths:
                continue
            seen_paths.add(path)

            try:
                data = cls._read_config_file(path)
            except OSError:
                continue
            except Exception as e:
                cls._log_config('error', 'Failed to read {}: {}'.format(path, e))
                cls._quarantine_corrupt_file(path)
                gc.collect()
                continue

            normalized = cls._normalize_config_data(data)
            loaded = cls._apply_config_data(normalized)
            cls._config_file_path = path
            cls._log_config(
                'info',
                'Loaded {} settings from {}'.format(len(loaded), path)
            )
            return loaded

        cls._log_config('info', 'Config file not found, using defaults')
        return []

    @classmethod
    def save_to_file(cls, filename=None):
        """Сохранение изменяемых настроек в JSON."""
        path = filename or cls.CONFIG_FILE
        try:
            with open(path, 'w') as f:
                json.dump(cls.get_mutable_settings(), f)
                f.flush()
            try:
                import os
                os.sync()
            except Exception:
                pass
            cls._config_file_path = path
            cls._config_loaded_keys = list(cls.get_mutable_settings().keys())
            cls._log_config('info', 'Saved settings to {}'.format(path))
            return True
        except Exception as e:
            cls._log_config('error', 'Failed to save {}: {}'.format(path, e))
            return False

    @classmethod
    def reset_mutable_settings(cls):
        """Сброс изменяемых настроек к значениям по умолчанию из config.py."""
        for key, value in SETTINGS_DEFAULTS.items():
            setattr(cls, key, value)


MUTABLE_SETTINGS = {
    'SENSOR_POLL_INTERVAL_MS': {'type': int, 'runtime': True, 'min': 2000, 'max': 3600000},
    'SENSOR_POLL_ENABLED': {'type': bool, 'runtime': True},
    'DISPLAY_EVENT_DURATION_MS': {'type': int, 'runtime': True, 'min': 500, 'max': 60000},
    'DISPLAY_IDLE_REFRESH_MS': {'type': int, 'runtime': True, 'min': 500, 'max': 60000},
    'STATION_NAME': {'type': str, 'runtime': True, 'min_len': 1, 'max_len': 32},
    'WEATHER_CITY': {'type': str, 'runtime': True, 'min_len': 1, 'max_len': 64},
    'WEATHER_UPDATE_INTERVAL': {'type': int, 'runtime': True, 'min': 60, 'max': 86400},
    'DEBUG': {'type': bool, 'runtime': True},
    'DHT_ENABLED': {'type': bool, 'runtime': True},
    'BMP280_ENABLED': {'type': bool, 'runtime': True},
    'CO2_ENABLED': {'type': bool, 'runtime': True},
    'DISPLAY_ENABLED': {'type': bool, 'runtime': True},
    'WEATHER_ENABLED': {'type': bool, 'runtime': True},
    'STATION_ID': {'type': str, 'runtime': False, 'min_len': 1, 'max_len': 32},
    'SERVER_PORT': {'type': int, 'runtime': False, 'min': 1, 'max': 65535},
}

SETTINGS_DEFAULTS = {key: getattr(Config, key) for key in MUTABLE_SETTINGS}
