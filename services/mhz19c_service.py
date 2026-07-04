import time
import machine
from utils.logger import logger


class MHZ19CService:
    """Сервис для работы с датчиком CO2 MH-Z19C по UART."""

    def __init__(self, uart_id=2, tx_pin=17, rx_pin=16, baudrate=9600, swap_tx_rx=False):
        self.uart_id = uart_id
        self.config_tx_pin = tx_pin
        self.config_rx_pin = rx_pin
        self.swap_tx_rx = swap_tx_rx
        self.baudrate = baudrate

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

        self._init_sensor()

    def _init_sensor(self):
        self.last_error = None

        try:
            self.uart = machine.UART(
                self.uart_id,
                baudrate=self.baudrate,
                bits=8,
                parity=None,
                stop=1,
                tx=machine.Pin(self.tx_pin),
                rx=machine.Pin(self.rx_pin),
                timeout=0
            )
            logger.info(
                "MHZ19C UART initialized: id={}, tx={}, rx={}, swap={}".format(
                    self.uart_id, self.tx_pin, self.rx_pin, self.swap_tx_rx
                )
            )
        except Exception as e:
            self.last_error = "Failed to init UART: {}".format(e)
            logger.error(self.last_error)
            self.uart = None
            return

        try:
            from mhz19c import MHZ19C
            self.sensor = MHZ19C(self.uart)
            logger.info("MHZ19C driver initialized")
        except Exception as e:
            self.last_error = "Cannot import/init MHZ19C driver: {}".format(e)
            logger.error(self.last_error)
            self.sensor = None

    def _build_diagnostics(self, rx_buffer=None):
        from mhz19c import MHZ19C

        if rx_buffer is None and self.sensor is not None:
            rx_buffer = self.sensor.last_rx_buffer

        byte_values = []
        if rx_buffer:
            for item in rx_buffer:
                if isinstance(item, str):
                    byte_values.append(int(item, 16))
                else:
                    byte_values.append(int(item))

        analysis = MHZ19C.analyze_buffer(bytes(byte_values))
        if analysis.get("looks_like_pms5003"):
            analysis["summary"] = analysis["summary"].format(self.rx_pin)

        diagnostics = {
            "uart_id": self.uart_id,
            "tx_pin": self.tx_pin,
            "rx_pin": self.rx_pin,
            "config_tx_pin": self.config_tx_pin,
            "config_rx_pin": self.config_rx_pin,
            "swap_tx_rx": self.swap_tx_rx,
            "baudrate": self.baudrate,
            "rx_analysis": analysis,
            "last_rx_buffer": rx_buffer,
            "wiring_note": "ESP GPIO{} (TX) -> sensor Rx, GPIO{} (RX) <- sensor Tx, Vin -> 5V".format(
                self.tx_pin, self.rx_pin
            ),
            "suggested_pins": "If current RX pin has foreign traffic, try TX=25 RX=26"
        }
        self.last_diagnostics = diagnostics
        return diagnostics

    def probe(self):
        """Диагностика линии UART без требования валидного ответа MH-Z19C."""
        if self.sensor is None:
            return {
                "ok": False,
                "error": self.last_error or "Sensor not initialized"
            }

        try:
            raw = self.sensor.sniff(wait_ms=500)
            diagnostics = self._build_diagnostics(self.sensor.last_rx_buffer)
            diagnostics["sent_command"] = [hex(b) for b in self.sensor.READ_CMD]
            diagnostics["ok"] = diagnostics["rx_analysis"].get("has_mhz19_header", False)
            return diagnostics
        except Exception as e:
            self.last_error = "MHZ19C probe error: {}".format(e)
            logger.error(self.last_error)
            return {
                "ok": False,
                "error": self.last_error
            }

    def read(self, force=False, max_age_ms=5000):
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
                "cached": True
            }

        last_exception = None
        for attempt in range(2):
            try:
                data = self.sensor.read_co2()
                co2 = int(data["co2_ppm"])

                if co2 < 0 or co2 > 50000:
                    logger.warning("MHZ19C returned suspicious value: {}".format(co2))
                    last_exception = OSError("Suspicious CO2 value: {}".format(co2))
                    time.sleep_ms(100)
                    continue

                self.last_co2_ppm = co2
                self.last_read_time = now
                self.last_error = None
                self._build_diagnostics()

                return {
                    "co2_ppm": co2,
                    "cached": False
                }
            except Exception as e:
                last_exception = e
                logger.warning(
                    "MHZ19C read attempt {} failed: {}".format(attempt + 1, e)
                )
                time.sleep_ms(100)

        self.last_error = "MHZ19C read error: {}".format(last_exception)
        self._build_diagnostics()
        logger.error(self.last_error)
        return None

    def set_abc(self, enabled):
        if self.sensor is None:
            return False
        try:
            self.sensor.set_abc(bool(enabled))
            return True
        except Exception as e:
            self.last_error = "MHZ19C ABC error: {}".format(e)
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
            "uart_id": self.uart_id,
            "tx_pin": self.tx_pin,
            "rx_pin": self.rx_pin,
            "config_tx_pin": self.config_tx_pin,
            "config_rx_pin": self.config_rx_pin,
            "swap_tx_rx": self.swap_tx_rx,
            "baudrate": self.baudrate,
            "last_error": self.last_error,
            "last_co2_ppm": self.last_co2_ppm,
            "last_read_time": self.last_read_time,
            "last_raw_response": None,
            "last_rx_buffer": None,
            "warmup_note": "After power-on allow ~3 minutes for stable readings"
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
