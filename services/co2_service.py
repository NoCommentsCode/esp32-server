import gc
import time
import machine
from utils.logger import logger


class CO2Service:
    """Сервис CO2: поддержка C8 и MH-Z19C."""

    SUPPORTED_TYPES = ("c8", "mhz19c")
    DEFAULT_READ_TIMEOUT_MS = 1500
    POLL_READ_TIMEOUT_MS = 1200

    def __init__(
        self,
        sensor_type="c8",
        uart_id=2,
        tx_pin=17,
        rx_pin=16,
        baudrate=9600,
        swap_tx_rx=False,
        c8_mode="active"
    ):
        self.sensor_type = sensor_type.lower()
        self.uart_id = uart_id
        self.config_tx_pin = tx_pin
        self.config_rx_pin = rx_pin
        self.swap_tx_rx = swap_tx_rx
        self.baudrate = baudrate
        self.c8_mode = c8_mode

        if swap_tx_rx:
            self.tx_pin = rx_pin
            self.rx_pin = tx_pin
        else:
            self.tx_pin = tx_pin
            self.rx_pin = rx_pin

        self.uart = None
        self.sensor = None
        self.last_error = None
        self.last_diagnostics = None
        self.last_read_time = 0
        self.last_co2_ppm = None
        self.last_mode = None
        self._init_failed = False

    @property
    def init_failed(self):
        return self._init_failed

    def ensure_initialized(self):
        """Однократная инициализация UART. Повтор не делаем — на ESP32 deinit/reinit ломает память."""
        if self.sensor is not None:
            return True
        if self._init_failed:
            return False

        gc.collect()
        logger.info("CO2 init, free mem: {}".format(gc.mem_free()))
        self._init_sensor()

        if self.sensor is None:
            self._init_failed = True
            return False
        return True

    def _init_sensor(self):
        self.last_error = None

        if self.sensor_type not in self.SUPPORTED_TYPES:
            self.last_error = "Unsupported CO2 sensor type: {}".format(self.sensor_type)
            logger.error(self.last_error)
            return

        if self.uart is None and not self._init_uart():
            return

        try:
            if self.sensor_type == "c8":
                from c8_co2 import C8CO2
                self.sensor = C8CO2(self.uart, mode=self.c8_mode)
            else:
                from mhz19c import MHZ19C
                self.sensor = MHZ19C(self.uart)
            logger.info("CO2 driver initialized: {}".format(self.sensor_type))
        except Exception as e:
            self.last_error = "Cannot import/init CO2 driver: {}".format(e)
            logger.error(self.last_error)
            self.sensor = None

    def _init_uart(self):
        if self.uart is not None:
            return True

        try:
            gc.collect()
            self.uart = machine.UART(
                self.uart_id,
                baudrate=self.baudrate,
                bits=8,
                parity=None,
                stop=1,
                tx=self.tx_pin,
                rx=self.rx_pin,
                timeout=0,
            )
            logger.info(
                "CO2 UART initialized: type={}, id={}, tx={}, rx={}".format(
                    self.sensor_type, self.uart_id, self.tx_pin, self.rx_pin
                )
            )
            return True
        except Exception as e:
            self.last_error = "Failed to init UART: {}".format(e)
            logger.error(self.last_error)
            self.uart = None
            return False

    def _analyze_buffer(self, rx_buffer):
        byte_values = []
        if rx_buffer:
            for item in rx_buffer:
                if isinstance(item, str):
                    byte_values.append(int(item, 16))
                else:
                    byte_values.append(int(item))

        raw = bytes(byte_values)
        if self.sensor_type == "c8":
            from c8_co2 import C8CO2
            return C8CO2.analyze_buffer(raw)

        from mhz19c import MHZ19C
        analysis = MHZ19C.analyze_buffer(raw)
        if analysis.get("looks_like_pms5003"):
            analysis["summary"] = analysis["summary"].format(self.rx_pin)
        return analysis

    def _build_diagnostics(self, rx_buffer=None):
        if rx_buffer is None and self.sensor is not None:
            rx_buffer = self.sensor.last_rx_buffer

        analysis = self._analyze_buffer(rx_buffer)
        diagnostics = {
            "sensor_type": self.sensor_type,
            "uart_id": self.uart_id,
            "tx_pin": self.tx_pin,
            "rx_pin": self.rx_pin,
            "config_tx_pin": self.config_tx_pin,
            "config_rx_pin": self.config_rx_pin,
            "swap_tx_rx": self.swap_tx_rx,
            "baudrate": self.baudrate,
            "c8_mode": self.c8_mode if self.sensor_type == "c8" else None,
            "rx_analysis": analysis,
            "last_rx_buffer": rx_buffer,
            "init_failed": self._init_failed,
            "wiring_note": "ESP GPIO{} (TX) -> sensor Rx, GPIO{} (RX) <- sensor Tx, Vin -> 5V".format(
                self.tx_pin, self.rx_pin
            )
        }
        self.last_diagnostics = diagnostics
        return diagnostics

    def probe(self, wait_ms=800):
        if not self.ensure_initialized():
            return {
                "ok": False,
                "error": self.last_error or "Sensor not initialized"
            }

        try:
            self.sensor.sniff(wait_ms=wait_ms)
            diagnostics = self._build_diagnostics(self.sensor.last_rx_buffer)
            detected = diagnostics["rx_analysis"].get("detected_protocol")
            if self.sensor_type == "c8":
                diagnostics["ok"] = detected in ("c8_active", "c8_query")
            else:
                diagnostics["ok"] = diagnostics["rx_analysis"].get("has_mhz19_header", False)
            return diagnostics
        except Exception as e:
            self.last_error = "CO2 probe error: {}".format(e)
            logger.error(self.last_error)
            return {
                "ok": False,
                "error": self.last_error
            }

    def read(self, force=False, max_age_ms=5000, timeout_ms=None):
        if timeout_ms is None:
            timeout_ms = self.DEFAULT_READ_TIMEOUT_MS

        if not self.ensure_initialized():
            self._build_diagnostics()
            return None

        now = time.ticks_ms()

        if (
            not force and
            self.last_co2_ppm is not None and
            time.ticks_diff(now, self.last_read_time) < max_age_ms
        ):
            return {
                "co2_ppm": self.last_co2_ppm,
                "cached": True,
                "mode": self.last_mode
            }

        last_exception = None
        for attempt in range(2):
            try:
                data = self._read_co2(timeout_ms)
                co2 = int(data["co2_ppm"])

                if co2 < 0 or co2 > 50000:
                    logger.warning("CO2 sensor returned suspicious value: {}".format(co2))
                    last_exception = OSError("Suspicious CO2 value: {}".format(co2))
                    time.sleep_ms(50)
                    continue

                self.last_co2_ppm = co2
                self.last_read_time = now
                self.last_mode = data.get("mode")
                self.last_error = None
                self._build_diagnostics()

                return {
                    "co2_ppm": co2,
                    "cached": False,
                    "mode": self.last_mode
                }
            except Exception as e:
                last_exception = e
                logger.warning(
                    "CO2 read attempt {} failed: {}".format(attempt + 1, e)
                )
                time.sleep_ms(50)

        self.last_error = "CO2 read error: {}".format(last_exception)
        self._build_diagnostics()
        logger.error(self.last_error)
        return None

    def _read_co2(self, timeout_ms):
        if self.sensor_type == "c8":
            from c8_co2 import C8CO2
            if self.c8_mode == "query":
                co2, frame = self.sensor.read_co2_query(timeout_ms=timeout_ms)
                mode = "query"
            else:
                co2, frame = self.sensor.read_co2_active(timeout_ms=timeout_ms)
                mode = "active"
            return {
                "co2_ppm": co2,
                "raw": frame,
                "mode": mode
            }

        data = self.sensor.read_co2()
        return data

    def set_abc(self, enabled):
        if self.sensor_type != "mhz19c":
            self.last_error = "ABC is supported only for MH-Z19C"
            return False
        if not self.ensure_initialized():
            return False
        try:
            self.sensor.set_abc(bool(enabled))
            return True
        except Exception as e:
            self.last_error = "CO2 ABC error: {}".format(e)
            logger.error(self.last_error)
            return False

    def _format_raw(self, raw):
        if raw is None:
            return None
        try:
            return [hex(b) for b in raw]
        except Exception:
            return None

    def get_status(self, probe=False):
        status = {
            "initialized": self.sensor is not None,
            "init_failed": self._init_failed,
            "sensor_type": self.sensor_type,
            "uart_id": self.uart_id,
            "tx_pin": self.tx_pin,
            "rx_pin": self.rx_pin,
            "config_tx_pin": self.config_tx_pin,
            "config_rx_pin": self.config_rx_pin,
            "swap_tx_rx": self.swap_tx_rx,
            "baudrate": self.baudrate,
            "c8_mode": self.c8_mode if self.sensor_type == "c8" else None,
            "last_error": self.last_error,
            "last_co2_ppm": self.last_co2_ppm,
            "last_read_time": self.last_read_time,
            "last_mode": self.last_mode,
            "last_raw_response": None,
            "last_rx_buffer": None,
            "warmup_note": "After power-on allow ~1-3 minutes for stable readings"
        }

        if self.sensor is not None:
            status["last_raw_response"] = self._format_raw(self.sensor.last_raw_response)
            status["last_rx_buffer"] = self.sensor.last_rx_buffer

        if probe:
            status["probe"] = self.probe()
        elif self.last_diagnostics:
            status["diagnostics"] = self.last_diagnostics
        else:
            status["diagnostics"] = self._build_diagnostics()

        return status

    def get_diagnostics(self):
        if self.last_diagnostics:
            return self.last_diagnostics
        return self._build_diagnostics()
