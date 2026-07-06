import time
import machine
from utils.logger import logger


class DisplayService:
    """Сервис отладочного I2C OLED (SSD1306, двухцветный GMO09605)."""

    FONT_HEIGHT = 8
    CHARS_PER_LINE = 21

    def __init__(
        self,
        i2c_id=0,
        sda_pin=21,
        scl_pin=22,
        i2c_freq=400000,
        width=128,
        height=64,
        address=0x3C,
        color_split_y=16,
        event_duration_ms=2000,
        idle_refresh_ms=3000,
        wifi_manager=None,
        dht_service=None,
        bmp280_service=None
    ):
        self.i2c_id = i2c_id
        self.sda_pin = sda_pin
        self.scl_pin = scl_pin
        self.i2c_freq = i2c_freq
        self.width = width
        self.height = height
        self.address = address
        self.color_split_y = color_split_y
        self.event_duration_ms = event_duration_ms
        self.idle_refresh_ms = idle_refresh_ms

        self.wifi_manager = wifi_manager
        self.dht_service = dht_service
        self.bmp280_service = bmp280_service

        self.i2c = None
        self.display = None
        self.enabled = False
        self._event_until_ms = 0
        self._last_idle_draw_ms = 0

        self._init_display()

    def _import_ssd1306_class(self):
        candidates = [
            ('lib.ssd1306', 'SSD1306_I2C'),
            ('ssd1306', 'SSD1306_I2C'),
        ]
        for module_name, class_name in candidates:
            try:
                module = __import__(module_name, None, None, [class_name])
                return getattr(module, class_name)
            except Exception:
                pass

        logger.warning(
            "Display disabled: cannot import SSD1306 driver. "
            "Expected lib/ssd1306.py or ssd1306.py on device"
        )
        return None

    def _init_display(self):
        ssd1306_class = self._import_ssd1306_class()
        if ssd1306_class is None:
            return

        candidate_addresses = [self.address]
        if self.address != 0x3D:
            candidate_addresses.append(0x3D)
        if self.address != 0x3C:
            candidate_addresses.append(0x3C)

        try:
            self.i2c = machine.I2C(
                self.i2c_id,
                sda=machine.Pin(self.sda_pin),
                scl=machine.Pin(self.scl_pin),
                freq=self.i2c_freq
            )
            scan_result = self.i2c.scan()
            logger.info("Display I2C scan: {}".format([hex(addr) for addr in scan_result]))

            for addr in candidate_addresses:
                if addr in scan_result:
                    self.address = addr
                    break

            self.display = ssd1306_class(
                self.width,
                self.height,
                self.i2c,
                addr=self.address
            )
            self.enabled = True
            self._draw_boot_screen()
            self._draw_idle()
            logger.info(
                "Display initialized: I2C({}) sda={} scl={} addr=0x{:02X}".format(
                    self.i2c_id,
                    self.sda_pin,
                    self.scl_pin,
                    self.address
                )
            )
        except Exception as e:
            self.enabled = False
            self.display = None
            self.i2c = None
            logger.error("Display init failed: {}".format(e))

    def _fit_text(self, text, max_len=None):
        if max_len is None:
            max_len = self.CHARS_PER_LINE
        safe_text = str(text)
        if len(safe_text) <= max_len:
            return safe_text
        if max_len <= 3:
            return safe_text[:max_len]
        return safe_text[:max_len - 3] + "..."

    def _line_y(self, line_index):
        return line_index * self.FONT_HEIGHT

    def _clear(self):
        if self.enabled and self.display:
            self.display.fill(0)

    def _draw_text(self, line_index, text):
        if not self.enabled or not self.display:
            return

        y = self._line_y(line_index)
        self.display.text(self._fit_text(text), 0, y)

    def _flush(self):
        if self.enabled and self.display:
            self.display.show()

    def _draw_boot_screen(self):
        if not self.enabled:
            return

        self._clear()
        self._draw_text(0, "ESP32 Server")
        self._draw_text(1, "Display ready")
        self._flush()

    def _wifi_line(self):
        if self.wifi_manager and self.wifi_manager.is_connected:
            try:
                ssid = self.wifi_manager.wlan.config('essid')
            except Exception:
                ssid = "connected"
            return "WiFi: {}".format(self._fit_text(ssid, 15))
        return "WiFi: offline"

    def _ip_line(self):
        if self.wifi_manager and self.wifi_manager.is_connected:
            ip = self.wifi_manager.get_ip()
            if ip:
                return "IP: {}".format(ip)
        return "IP: ---"

    def _format_temp(self):
        if self.bmp280_service and self.bmp280_service.last_temperature is not None:
            return "{:.1f}".format(self.bmp280_service.last_temperature)
        if self.dht_service and self.dht_service.last_temperature is not None:
            return "{:.1f}".format(self.dht_service.last_temperature)
        return "--.-"

    def _format_humidity(self):
        if self.dht_service and self.dht_service.last_humidity is not None:
            return "{:.0f}".format(self.dht_service.last_humidity)
        return "--"

    def _format_pressure(self):
        if self.bmp280_service and self.bmp280_service.last_pressure_hpa is not None:
            return "{:.0f}".format(self.bmp280_service.last_pressure_hpa)
        return "----"

    def _status_label(self, status_code):
        code = int(status_code)
        if 200 <= code <= 299:
            return "OK"
        if 400 <= code <= 499:
            return "client err"
        if 500 <= code <= 599:
            return "server err"
        return "status"

    def show_wifi_status(self):
        """Обновить экран после подключения к Wi-Fi."""
        if not self.enabled:
            return
        self._draw_idle()

    def show_http_event(self, method, path, client_ip, status_code):
        """Показать HTTP-запрос на несколько секунд."""
        if not self.enabled:
            return

        self._clear()
        self._draw_text(0, "HTTP {}".format(int(status_code)))
        self._draw_text(1, "{} {}".format(method, self._fit_text(path, 16)))
        self._draw_text(2, "from {}".format(self._fit_text(client_ip, 16)))
        self._draw_text(3, "{} {}".format(int(status_code), self._status_label(status_code)))
        self._flush()

        self._event_until_ms = time.ticks_add(time.ticks_ms(), self.event_duration_ms)

    def _draw_idle(self):
        if not self.enabled:
            return

        self._clear()
        self._draw_text(0, self._wifi_line())
        self._draw_text(1, self._ip_line())
        self._draw_text(2, "T:{}C H:{}%".format(self._format_temp(), self._format_humidity()))
        self._draw_text(3, "P:{} hPa".format(self._format_pressure()))
        self._draw_text(4, "API :80 ready")
        self._flush()
        self._last_idle_draw_ms = time.ticks_ms()

    def tick(self):
        """Вернуть idle-экран после истечения HTTP-события."""
        if not self.enabled:
            return

        now = time.ticks_ms()
        in_event = time.ticks_diff(self._event_until_ms, now) > 0
        if in_event:
            return

        if time.ticks_diff(now, self._last_idle_draw_ms) >= self.idle_refresh_ms:
            self._draw_idle()
