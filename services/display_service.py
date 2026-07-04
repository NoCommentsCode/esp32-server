import time
import machine
from utils.logger import logger


class DisplayService:
    """Сервис для отображения статуса HTTP и данных датчиков на SPI дисплее."""

    COLOR_BLACK = 0x0000
    COLOR_WHITE = 0xFFFF
    COLOR_RED = 0xF800
    COLOR_GREEN = 0x07E0
    COLOR_BLUE = 0x001F
    COLOR_YELLOW = 0xFFE0
    COLOR_CYAN = 0x07FF
    COLOR_MAGENTA = 0xF81F
    COLOR_ORANGE = 0xFD20

    def __init__(
        self,
        spi_id=1,
        sck_pin=18,
        mosi_pin=23,
        miso_pin=None,
        baudrate=40000000,
        min_baudrate=5000000,
        use_soft_spi_fallback=True,
        spi_polarity=0,
        spi_phase=0,
        width=172,
        height=320,
        rotation=1,
        cs_pin=5,
        dc_pin=2,
        rst_pin=4,
        bl_pin=15,
        bl_active_high=True,
        use_bl_pwm=False,
        bl_pwm_freq=1000,
        event_duration_ms=2000,
        dht_service=None,
        bmp280_service=None
    ):
        self.spi_id = spi_id
        self.sck_pin = sck_pin
        self.mosi_pin = mosi_pin
        self.miso_pin = miso_pin
        self.baudrate = baudrate
        self.min_baudrate = min_baudrate
        self.use_soft_spi_fallback = use_soft_spi_fallback
        self.spi_polarity = spi_polarity
        self.spi_phase = spi_phase
        self.width = width
        self.height = height
        self.rotation = rotation
        self.cs_pin = cs_pin
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        self.bl_pin = bl_pin
        self.bl_active_high = bl_active_high
        self.use_bl_pwm = use_bl_pwm
        self.bl_pwm_freq = bl_pwm_freq
        self.event_duration_ms = event_duration_ms

        self.dht_service = dht_service
        self.bmp280_service = bmp280_service

        self.display = None
        self.backlight_pwm = None
        self.backlight_pin = None
        self.enabled = False
        self._event_until_ms = 0
        self._last_idle_draw_ms = 0
        self._idle_refresh_ms = 1500

        self._init_display()

    def _init_display(self):
        """Инициализация SPI и драйвера дисплея."""
        st7789_module = self._import_st7789_module()
        if st7789_module is None:
            return

        try:
            # Включаем подсветку как можно раньше, чтобы не гасла после загрузки.
            self._init_backlight()
            self._set_backlight(True)
            if not self._try_init_with_fallbacks(st7789_module):
                raise Exception("all ST7789 init attempts failed")

            self.enabled = True
            self._draw_boot_test()
            self._draw_idle()
            logger.info(
                "Display initialized: SPI({}) sck={} mosi={} mode={}/{} bl_pin={}".format(
                    self.spi_id,
                    self.sck_pin,
                    self.mosi_pin,
                    self.spi_polarity,
                    self.spi_phase,
                    self.bl_pin
                )
            )
        except Exception as e:
            self.enabled = False
            self.display = None
            logger.error("Display init failed: {}".format(e))
            self._set_backlight(True)

    def _import_st7789_module(self):
        """
        Пытается импортировать один из распространенных модулей драйвера.
        Возвращает модуль или None.
        """
        candidates = ["st7789", "st7789py"]
        for module_name in candidates:
            try:
                module = __import__(module_name)
                logger.info("Display driver module loaded: {}".format(module_name))
                return module
            except Exception:
                pass

        logger.warning(
            "Display disabled: cannot import ST7789 driver. "
            "Expected module: st7789.py or st7789py.py"
        )
        return None

    def _build_spi(self, baudrate, polarity, phase, soft=False):
        sck = machine.Pin(self.sck_pin)
        mosi = machine.Pin(self.mosi_pin)
        miso = machine.Pin(self.miso_pin) if self.miso_pin is not None else None

        if soft:
            return machine.SoftSPI(
                baudrate=baudrate,
                polarity=polarity,
                phase=phase,
                sck=sck,
                mosi=mosi,
                miso=miso
            )

        return machine.SPI(
            self.spi_id,
            baudrate=baudrate,
            polarity=polarity,
            phase=phase,
            sck=sck,
            mosi=mosi,
            miso=miso
        )

    def _try_build_display(self, st7789, spi_obj):
        reset_pin = machine.Pin(self.rst_pin, machine.Pin.OUT)
        cs_pin = machine.Pin(self.cs_pin, machine.Pin.OUT)
        dc_pin = machine.Pin(self.dc_pin, machine.Pin.OUT)

        # На разных портах st7789 порядок аргументов может отличаться.
        constructors = [
            (self.width, self.height),
            (self.height, self.width),
        ]

        for first, second in constructors:
            try:
                display = st7789.ST7789(
                    spi_obj,
                    first,
                    second,
                    reset=reset_pin,
                    cs=cs_pin,
                    dc=dc_pin,
                    rotation=self.rotation
                )
                display.init()
                return display
            except Exception:
                pass
        return None

    def _try_init_with_fallbacks(self, st7789):
        modes = [
            (self.spi_polarity, self.spi_phase),
            (0, 0),
            (1, 1),
            (1, 0),
            (0, 1),
        ]
        # Уберем дубликаты режимов, сохранив порядок.
        unique_modes = []
        for mode in modes:
            if mode not in unique_modes:
                unique_modes.append(mode)

        baudrates = [self.baudrate, 20000000, 10000000, self.min_baudrate]
        unique_baudrates = []
        for b in baudrates:
            if b not in unique_baudrates and b is not None and b > 0:
                unique_baudrates.append(b)

        transport_list = [False]
        if self.use_soft_spi_fallback:
            transport_list.append(True)

        for use_soft in transport_list:
            for baud in unique_baudrates:
                for polarity, phase in unique_modes:
                    try:
                        spi_obj = self._build_spi(baud, polarity, phase, soft=use_soft)
                        display = self._try_build_display(st7789, spi_obj)
                        if display:
                            self.spi = spi_obj
                            self.display = display
                            self.spi_polarity = polarity
                            self.spi_phase = phase
                            self.baudrate = baud
                            logger.info(
                                "Display init success: {}SPI baud={} mode={}/{}".format(
                                    "Soft" if use_soft else "HW",
                                    baud,
                                    polarity,
                                    phase
                                )
                            )
                            return True
                    except Exception:
                        pass

        return False

    def _draw_boot_test(self):
        """Короткий тест цветов при старте: удобно для диагностики железа."""
        if not self.display:
            return
        try:
            self.display.fill(self.COLOR_RED)
            time.sleep_ms(80)
            self.display.fill(self.COLOR_GREEN)
            time.sleep_ms(80)
            self.display.fill(self.COLOR_BLUE)
            time.sleep_ms(80)
            self.display.fill(self.COLOR_BLACK)
            self._draw_line(0, "Display ready", self.COLOR_GREEN)
        except Exception:
            self._clear()

    def _init_backlight(self):
        if self.bl_pin is None:
            return

        try:
            self.backlight_pin = machine.Pin(self.bl_pin, machine.Pin.OUT)
            if self.use_bl_pwm:
                self.backlight_pwm = machine.PWM(self.backlight_pin)
                self.backlight_pwm.freq(self.bl_pwm_freq)
        except Exception as e:
            logger.warning("Backlight init failed: {}".format(e))
            self.backlight_pin = None
            self.backlight_pwm = None

    def _set_backlight(self, enabled):
        if self.bl_pin is None:
            return

        on_level = 1 if self.bl_active_high else 0
        off_level = 0 if self.bl_active_high else 1
        level = on_level if enabled else off_level

        try:
            if self.backlight_pwm:
                duty = 65535 if level == 1 else 0
                self.backlight_pwm.duty_u16(duty)
            elif self.backlight_pin:
                self.backlight_pin.value(level)
        except Exception as e:
            logger.warning("Backlight set failed: {}".format(e))

    def _clear(self):
        if self.enabled and self.display:
            self.display.fill(self.COLOR_BLACK)

    def _text_line_y(self, line_index):
        return 10 + (line_index * 24)

    def _draw_line(self, line_index, text, color):
        if not self.enabled or not self.display:
            return

        y = self._text_line_y(line_index)
        safe_text = str(text)[:34]

        # Большинство портов st7789 имеют text(str, x, y, color).
        # Если текстовый API недоступен - просто не рисуем эту строку.
        try:
            self.display.text(safe_text, 8, y, color)
        except Exception:
            try:
                import vga1_8x8 as font
                self.display.text(font, safe_text, 8, y, color, self.COLOR_BLACK)
            except Exception:
                pass

    def _status_color(self, status_code):
        if 200 <= status_code <= 299:
            return self.COLOR_GREEN
        if 300 <= status_code <= 399:
            return self.COLOR_CYAN
        if 400 <= status_code <= 499:
            return self.COLOR_ORANGE
        if 500 <= status_code <= 599:
            return self.COLOR_RED
        return self.COLOR_WHITE

    def show_http_event(self, method, path, status_code):
        """Показать событие HTTP на 2 секунды."""
        if not self.enabled:
            return

        self._clear()
        self._draw_line(0, "HTTP request", self.COLOR_BLUE)
        self._draw_line(1, "{} {}".format(method, path), self.COLOR_WHITE)
        self._draw_line(2, "Status: {}".format(status_code), self._status_color(int(status_code)))
        self._event_until_ms = time.ticks_add(time.ticks_ms(), self.event_duration_ms)

    def _format_temp(self):
        if self.bmp280_service and self.bmp280_service.last_temperature is not None:
            return "{:.1f} C".format(self.bmp280_service.last_temperature)
        if self.dht_service and self.dht_service.last_temperature is not None:
            return "{:.1f} C".format(self.dht_service.last_temperature)
        return "--.- C"

    def _format_humidity(self):
        if self.dht_service and self.dht_service.last_humidity is not None:
            return "{:.1f} %".format(self.dht_service.last_humidity)
        return "--.- %"

    def _format_pressure(self):
        if self.bmp280_service and self.bmp280_service.last_pressure_hpa is not None:
            return "{:.1f} hPa".format(self.bmp280_service.last_pressure_hpa)
        return "----.- hPa"

    def _draw_idle(self):
        if not self.enabled:
            return

        self._clear()
        self._draw_line(0, "Last sensors", self.COLOR_WHITE)
        self._draw_line(1, "T: {}".format(self._format_temp()), self.COLOR_RED)
        self._draw_line(2, "H: {}".format(self._format_humidity()), self.COLOR_CYAN)
        self._draw_line(3, "P: {}".format(self._format_pressure()), self.COLOR_MAGENTA)
        self._last_idle_draw_ms = time.ticks_ms()

    def tick(self):
        """
        Метод периодического вызова из главного цикла.
        Возвращает экран в idle после истечения HTTP события.
        """
        if not self.enabled:
            return

        now = time.ticks_ms()
        in_event = time.ticks_diff(self._event_until_ms, now) > 0
        if in_event:
            return

        if time.ticks_diff(now, self._last_idle_draw_ms) >= self._idle_refresh_ms:
            self._draw_idle()
