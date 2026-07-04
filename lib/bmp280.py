try:
    import ustruct as struct
except Exception:
    import struct


class BMP280:
    """
    Minimal BMP280 driver for MicroPython.

    Supported constructors:
    - BMP280(i2c, address=0x76)
    - BMP280(i2c_dev=i2c, addr=0x76)
    """

    REG_CALIB = 0x88
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_PRESS_MSB = 0xF7
    REG_ID = 0xD0
    REG_RESET = 0xE0

    CHIP_ID = 0x58

    def __init__(self, i2c=None, address=0x76, i2c_dev=None, addr=None):
        self.i2c = i2c_dev if i2c_dev is not None else i2c
        self.address = addr if addr is not None else address

        if self.i2c is None:
            raise ValueError("I2C bus is required")

        chip_id = self._read_u8(self.REG_ID)
        if chip_id != self.CHIP_ID:
            raise OSError("BMP280 not found, chip id: {}".format(chip_id))

        self._load_calibration()
        self._configure()

    def _read_u8(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _read_s16_le(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2)
        value = struct.unpack("<h", data)[0]
        return value

    def _read_u16_le(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2)
        value = struct.unpack("<H", data)[0]
        return value

    def _load_calibration(self):
        # Temperature calibration
        self.dig_T1 = self._read_u16_le(0x88)
        self.dig_T2 = self._read_s16_le(0x8A)
        self.dig_T3 = self._read_s16_le(0x8C)

        # Pressure calibration
        self.dig_P1 = self._read_u16_le(0x8E)
        self.dig_P2 = self._read_s16_le(0x90)
        self.dig_P3 = self._read_s16_le(0x92)
        self.dig_P4 = self._read_s16_le(0x94)
        self.dig_P5 = self._read_s16_le(0x96)
        self.dig_P6 = self._read_s16_le(0x98)
        self.dig_P7 = self._read_s16_le(0x9A)
        self.dig_P8 = self._read_s16_le(0x9C)
        self.dig_P9 = self._read_s16_le(0x9E)

        self.t_fine = 0

    def _configure(self):
        # config: standby 500ms, filter x4, spi off
        self.i2c.writeto_mem(self.address, self.REG_CONFIG, bytes([0x90]))
        # ctrl_meas: temp x1, press x1, normal mode
        self.i2c.writeto_mem(self.address, self.REG_CTRL_MEAS, bytes([0x27]))

    def _read_raw(self):
        data = self.i2c.readfrom_mem(self.address, self.REG_PRESS_MSB, 6)
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        return adc_t, adc_p

    def _compensate_temperature(self, adc_t):
        var1 = (((adc_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (((((adc_t >> 4) - self.dig_T1) * ((adc_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = var1 + var2
        t = (self.t_fine * 5 + 128) >> 8
        return t / 100.0

    def _compensate_pressure(self, adc_p):
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = ((((1 << 47) + var1) * self.dig_P1) >> 33)

        if var1 == 0:
            return 0.0

        p = 1048576 - adc_p
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)
        # Pa -> hPa
        return p / 25600.0

    @property
    def temperature(self):
        adc_t, _ = self._read_raw()
        return self._compensate_temperature(adc_t)

    @property
    def pressure(self):
        adc_t, adc_p = self._read_raw()
        self._compensate_temperature(adc_t)
        return self._compensate_pressure(adc_p)
