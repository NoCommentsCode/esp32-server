import time
import machine
from utils.logger import logger


class BMP280Service:
    """Сервис для работы с датчиком BMP280 по I2C."""

    def __init__(self, i2c_id=0, scl_pin=22, sda_pin=21, address=0x76, i2c_freq=100000):
        self.i2c_id = i2c_id
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.address = address
        self.i2c_freq = i2c_freq

        self.i2c = None
        self.sensor = None
        self.driver_name = None
        self.last_error = None
        self.scan_result = []

        self.last_read_time = 0
        self.last_temperature = None
        self.last_pressure_hpa = None

        self._init_sensor()

    def _init_sensor(self):
        """Инициализация шины I2C и драйвера BMP280."""
        self.last_error = None

        # На разных ESP32 платах BMP280 может быть на 0x76 или 0x77,
        # а также на I2C(0) или I2C(1). Пробуем несколько комбинаций.
        candidate_ids = [self.i2c_id]
        if self.i2c_id == 0:
            candidate_ids.append(1)
        elif self.i2c_id == 1:
            candidate_ids.append(0)

        candidate_addresses = [self.address]
        if self.address != 0x77:
            candidate_addresses.append(0x77)
        if self.address != 0x76:
            candidate_addresses.append(0x76)

        for bus_id in candidate_ids:
            if self._try_init_i2c(bus_id):
                found_addr = self._probe_any_device(candidate_addresses)
                if found_addr is None:
                    continue

                self.address = found_addr
                self.i2c_id = bus_id
                if self._try_init_driver():
                    logger.info("BMP280 driver initialized: {}".format(self.driver_name))
                    return

        # Fallback: для части прошивок аппаратный I2C может не подняться
        # с выбранным ID, но работает SoftI2C на тех же пинах.
        if self._try_init_soft_i2c():
            found_addr = self._probe_any_device(candidate_addresses)
            if found_addr is not None:
                self.address = found_addr
                if self._try_init_driver():
                    logger.info("BMP280 driver initialized via SoftI2C: {}".format(self.driver_name))
                    return

        if self.last_error is None:
            self.last_error = "BMP280 init failed: device/driver not available"
        logger.error(self.last_error)

    def _try_init_i2c(self, bus_id):
        try:
            self.i2c = machine.I2C(
                bus_id,
                scl=machine.Pin(self.scl_pin),
                sda=machine.Pin(self.sda_pin),
                freq=self.i2c_freq
            )
            logger.info(
                "BMP280 I2C initialized: id={}, scl={}, sda={}".format(
                    bus_id, self.scl_pin, self.sda_pin
                )
            )
            return True
        except Exception as e:
            self.last_error = "Failed to init I2C({}): {}".format(bus_id, e)
            logger.warning(self.last_error)
            self.i2c = None
            return False

    def _try_init_soft_i2c(self):
        try:
            self.i2c = machine.SoftI2C(
                scl=machine.Pin(self.scl_pin),
                sda=machine.Pin(self.sda_pin),
                freq=self.i2c_freq
            )
            self.i2c_id = -1
            logger.info(
                "BMP280 SoftI2C initialized: scl={}, sda={}".format(
                    self.scl_pin, self.sda_pin
                )
            )
            return True
        except Exception as e:
            self.last_error = "Failed to init SoftI2C: {}".format(e)
            logger.warning(self.last_error)
            self.i2c = None
            return False

    def _probe_device(self):
        """Проверка наличия устройства на шине по адресу."""
        if self.i2c is None:
            return False
        try:
            devices = self.i2c.scan()
            self.scan_result = devices
            return self.address in devices
        except Exception as e:
            self.last_error = "BMP280 scan failed: {}".format(e)
            logger.error(self.last_error)
            return False

    def _probe_any_device(self, addresses):
        if self.i2c is None:
            return None
        try:
            devices = self.i2c.scan()
            self.scan_result = devices
            for addr in addresses:
                if addr in devices:
                    logger.info("BMP280 found at address 0x{:02X}".format(addr))
                    return addr
            self.last_error = "BMP280 not found. I2C scan: {}".format(devices)
            logger.warning(self.last_error)
            return None
        except Exception as e:
            self.last_error = "BMP280 scan failed: {}".format(e)
            logger.error(self.last_error)
            return None

    def _try_init_driver(self):
        """
        Пытаемся инициализировать один из популярных MicroPython-драйверов BMP280.
        Поддерживаем два распространенных API:
        1) BMP280(i2c_dev=..., addr=...)
        2) BMP280(i2c=..., address=...)
        """
        try:
            from bmp280 import BMP280
        except Exception as e:
            self.last_error = "Cannot import bmp280 driver: {}".format(e)
            logger.error(self.last_error)
            self.sensor = None
            return False

        # Вариант 1: параметры i2c_dev/addr
        try:
            self.sensor = BMP280(i2c_dev=self.i2c, addr=self.address)
            self.driver_name = "bmp280.BMP280(i2c_dev, addr)"
            return True
        except Exception:
            pass

        # Вариант 2: параметры i2c/address
        try:
            self.sensor = BMP280(i2c=self.i2c, address=self.address)
            self.driver_name = "bmp280.BMP280(i2c, address)"
            return True
        except Exception as e:
            self.last_error = "BMP280 constructor not supported by current driver: {}".format(e)
            logger.error(self.last_error)
            self.sensor = None
            return False

    def read(self, force=False, max_age_ms=2000):
        """
        Чтение данных с датчика.

        Args:
            force: принудительное чтение (игнорирует кэш)
            max_age_ms: максимальный возраст кэша в миллисекундах

        Returns:
            dict или None при ошибке
        """
        if self.sensor is None:
            return None

        now = time.ticks_ms()

        if (
            not force and
            self.last_temperature is not None and
            self.last_pressure_hpa is not None and
            time.ticks_diff(now, self.last_read_time) < max_age_ms
        ):
            return {
                "temperature": self.last_temperature,
                "pressure_hpa": self.last_pressure_hpa,
                "pressure_pa": self.last_pressure_hpa * 100.0,
                "pressure_mmhg": self.last_pressure_hpa * 0.750062,
                "cached": True
            }

        try:
            temp, pressure_hpa = self._read_raw_values()
            if temp is None or pressure_hpa is None:
                return None

            self.last_temperature = float(temp)
            self.last_pressure_hpa = float(pressure_hpa)
            self.last_read_time = now

            return {
                "temperature": self.last_temperature,
                "pressure_hpa": self.last_pressure_hpa,
                "pressure_pa": self.last_pressure_hpa * 100.0,
                "pressure_mmhg": self.last_pressure_hpa * 0.750062,
                "cached": False
            }
        except Exception as e:
            logger.error("BMP280 read error: {}".format(e))
            return None

    def _read_raw_values(self):
        """
        Получение сырых значений из драйвера.
        Поддерживает несколько вариантов API у разных библиотек.
        """
        # Вариант A: свойства temperature / pressure
        try:
            temp = self.sensor.temperature
            pressure = self.sensor.pressure
            # У части драйверов pressure в Pa, у части в hPa
            pressure_hpa = pressure / 100.0 if pressure > 2000 else pressure
            return temp, pressure_hpa
        except Exception:
            pass

        # Вариант B: методы temperature / pressure
        try:
            temp = self.sensor.temperature()
            pressure = self.sensor.pressure()
            pressure_hpa = pressure / 100.0 if pressure > 2000 else pressure
            return temp, pressure_hpa
        except Exception:
            pass

        # Вариант C: метод values() -> tuple/list
        try:
            values = self.sensor.values
            if callable(values):
                values = values()
            if values and len(values) >= 2:
                temp = values[0]
                pressure = values[1]
                pressure_hpa = pressure / 100.0 if pressure > 2000 else pressure
                return temp, pressure_hpa
        except Exception:
            pass

        raise Exception("Unsupported BMP280 driver API")

    def get_status(self):
        """Получить статус сервиса/датчика."""
        return {
            "initialized": self.sensor is not None,
            "driver": self.driver_name,
            "i2c_id": self.i2c_id,
            "scl_pin": self.scl_pin,
            "sda_pin": self.sda_pin,
            "address": self.address,
            "scan_result": self.scan_result,
            "last_error": self.last_error,
            "last_temperature": self.last_temperature,
            "last_pressure_hpa": self.last_pressure_hpa,
            "last_read_time": self.last_read_time
        }
