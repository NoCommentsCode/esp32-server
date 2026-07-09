import time
from utils.logger import logger


class SensorPollingService:
    """Фоновое чтение датчиков по таймеру."""

    def __init__(
        self,
        dht_service=None,
        bmp280_service=None,
        co2_service=None,
        interval_ms=5000,
        enabled=True
    ):
        self.dht_service = dht_service
        self.bmp280_service = bmp280_service
        self.co2_service = co2_service
        self.interval_ms = interval_ms
        self.enabled = enabled
        self._last_poll_ms = 0

    def poll_now(self):
        """Принудительное чтение всех датчиков."""
        return self._poll_sensors()

    def tick(self):
        """Периодический опрос. Возвращает True, если были обновления."""
        if not self.enabled:
            return False

        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_poll_ms) < self.interval_ms:
            return False

        updated = self._poll_sensors()
        self._last_poll_ms = now
        return updated

    def _poll_sensors(self):
        updated = False

        if self.dht_service:
            try:
                if self.dht_service.read(force=True):
                    updated = True
            except Exception as e:
                logger.warning("DHT poll error: {}".format(e))

        if self.bmp280_service:
            try:
                if self.bmp280_service.read(force=True):
                    updated = True
            except Exception as e:
                logger.warning("BMP280 poll error: {}".format(e))

        if self.co2_service:
            try:
                if self.co2_service.read(force=True):
                    updated = True
            except Exception as e:
                logger.warning("CO2 poll error: {}".format(e))

        if updated:
            logger.debug("Sensor poll completed with updates")

        return updated

    def get_status(self):
        return {
            'enabled': self.enabled,
            'interval_ms': self.interval_ms,
            'last_poll_ms': self._last_poll_ms
        }
