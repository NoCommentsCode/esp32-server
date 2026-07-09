import time
import machine
from utils.logger import logger


class CO2Service:
    """Сервис CO2: поддержка C8 и MH-Z19C."""

    SUPPORTED_TYPES = ("c8", "mhz19c")

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

        self._init_sensor()

    def _init_sensor(self):
        self.last_error = None

        if self.sensor_type not in self.SUPPORTED_TYPES:
            self.last_error = "Unsupported CO2 sensor type: {}".format(self.sensor_type)
            logger.error(self.last_error)
            return

        if not self._init_uart():
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
        try:
            if self.uart is not None:
                try:
                    self.uart.deinit()
                except Exception:
                    pass
                self.uart = None

            base_kwargs = {
                'baudrate': self.baudrate,
                'bits': 8,
                'parity': None,
                'stop': 1,
                'tx': self.tx_pin,
                'rx': self.rx_pin,
                'timeout': 0,
            }
            try:
                self.uart = machine.UART(self.uart_id, rxbuf=512, **base_kwargs)
            except TypeError:
                self.uart = machine.UART(self.uart_id, **base_kwargs)

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

    def _reinit_if_needed(self):
        if self.sensor is None:
            self._init_sensor()
            return self.sensor is not None

        analysis = self._analyze_buffer(self.sensor.last_rx_buffer)
        if analysis.get('byte_count', 0) == 0:
            logger.warning("CO2 RX silent, reinitializing UART")
            self.sensor = None
            self._init_sensor()
        return self.sensor is not None

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
            "wiring_note": "ESP GPIO{} (TX) -> sensor Rx, GPIO{} (RX) <- sensor Tx, Vin -> 5V".format(
                self.tx_pin, self.rx_pin
            )
        }
        self.last_diagnostics = diagnostics
        return diagnostics

    def probe(self):
        if self.sensor is None:
            return {
                "ok": False,
                "error": self.last_error or "Sensor not initialized"
            }

        try:
            if self.sensor_type == "c8":
                raw = self.sensor.sniff(wait_ms=1200)
            else:
                raw = self.sensor.sniff(wait_ms=500)

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

    def read(self, force=False, max_age_ms=5000):
        if self.sensor is None:
            self._init_sensor()
        if self.sensor is None:
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
                if force and attempt > 0:
                    self._reinit_if_needed()

                data = self.sensor.read_co2()
                co2 = int(data["co2_ppm"])

                if co2 < 0 or co2 > 50000:
                    logger.warning("CO2 sensor returned suspicious value: {}".format(co2))
                    last_exception = OSError("Suspicious CO2 value: {}".format(co2))
                    time.sleep_ms(100)
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
                time.sleep_ms(100)

        self.last_error = "CO2 read error: {}".format(last_exception)
        self._build_diagnostics()
        logger.error(self.last_error)
        return None

    def set_abc(self, enabled):
        if self.sensor_type != "mhz19c":
            self.last_error = "ABC is supported only for MH-Z19C"
            return False
        if self.sensor is None:
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
