import time


class MHZ19C:
    """
    Драйвер датчика CO2 MH-Z19C по UART.

    Протокол: 9600 8N1, 9-байтовые кадры.
    Чтение только через uart.any() — без блокирующих read().
    """

    CMD_READ_CO2 = 0x86
    CMD_SET_ABC = 0x79
    CMD_CALIBRATE_ZERO = 0x87
    CMD_RESET = 0x99

    READ_CMD = bytes([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])

    def __init__(self, uart):
        self.uart = uart
        self.last_raw_response = None
        self.last_rx_buffer = None
        self._flush()

    def _flush(self):
        for _ in range(64):
            available = self.uart.any()
            if not available:
                break
            self.uart.read(available)

    @staticmethod
    def _checksum(payload):
        total = sum(payload) & 0xFF
        return (0x100 - total) & 0xFF

    def _build_command(self, command, data=None):
        if data is None:
            data = [0x00, 0x00, 0x00, 0x00, 0x00]
        payload = [0x01, command] + list(data[:5])
        return bytes([0xFF] + payload + [self._checksum(payload)])

    def _find_valid_frame(self, buffer):
        limit = len(buffer) - 8
        for index in range(limit):
            if buffer[index] != 0xFF:
                continue

            frame = buffer[index:index + 9]
            if len(frame) < 9:
                continue

            if frame[8] != self._checksum(frame[1:8]):
                continue

            return bytes(frame)

        return None

    def _read_frame(self, timeout_ms=1200):
        buffer = bytearray()
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)

        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            available = self.uart.any()
            if available:
                chunk = self.uart.read(available)
                if chunk:
                    buffer.extend(chunk)
                    if len(buffer) > 64:
                        buffer = buffer[-64:]

                    frame = self._find_valid_frame(buffer)
                    if frame is not None:
                        self.last_raw_response = frame
                        self.last_rx_buffer = [hex(b) for b in buffer]
                        return frame

            time.sleep_ms(20)

        self.last_rx_buffer = [hex(b) for b in buffer] if buffer else []
        raise OSError("MHZ19C response timeout")

    def _send_command(self, command, data=None, timeout_ms=1200):
        self._flush()
        packet = self._build_command(command, data)
        self.uart.write(packet)
        time.sleep_ms(100)
        return self._read_frame(timeout_ms=timeout_ms)

    @staticmethod
    def _parse_co2(frame):
        if frame[1] == 0x86:
            return frame[2] * 256 + frame[3]
        if frame[1] == 0x01 and frame[2] == 0x86:
            return frame[3] * 256 + frame[4]
        raise OSError("MHZ19C unexpected response format")

    def read_co2(self):
        """
        Чтение концентрации CO2 в ppm.

        Returns:
            dict: {'co2_ppm': int, 'raw': bytes}
        """
        frame = self._send_command(self.CMD_READ_CO2)
        co2 = self._parse_co2(frame)
        return {
            "co2_ppm": co2,
            "raw": frame
        }

    def set_abc(self, enabled):
        data = [0x00, 0x00, 0x00, 0xA0 if enabled else 0x00, 0x00]
        self._send_command(self.CMD_SET_ABC, data=data, timeout_ms=2000)

    def calibrate_zero(self):
        self._send_command(self.CMD_CALIBRATE_ZERO, timeout_ms=3000)

    def reset(self):
        self._send_command(self.CMD_RESET, timeout_ms=2000)
        time.sleep_ms(1000)
        self._flush()

    def sniff(self, wait_ms=500):
        """
        Отправить команду чтения и собрать сырые байты с линии RX.
        Не требует валидного кадра MH-Z19C.
        """
        self._flush()
        self.uart.write(self.READ_CMD)
        time.sleep_ms(wait_ms)

        buffer = bytearray()
        for _ in range(32):
            available = self.uart.any()
            if available:
                chunk = self.uart.read(available)
                if chunk:
                    buffer.extend(chunk)
            time.sleep_ms(10)

        self.last_rx_buffer = [hex(b) for b in buffer]
        return bytes(buffer)

    @staticmethod
    def analyze_buffer(buffer):
        """Анализ сырых байтов на линии RX."""
        if not buffer:
            return {
                "byte_count": 0,
                "has_mhz19_header": False,
                "looks_like_pms5003": False,
                "summary": "RX line is silent — check sensor Tx wire and common GND"
            }

        has_ff = 0xFF in buffer
        looks_like_pms = len(buffer) >= 2 and buffer[0] == 0x42 and buffer[1] == 0x4D

        if looks_like_pms and not has_ff:
            summary = (
                "RX receives 0x42 0x4D (PMS5003/dust sensor protocol), not MH-Z19C (0xFF). "
                "GPIO {} is likely connected to another UART device or wrong wire."
            )
        elif not has_ff:
            summary = (
                "UART data present but no MH-Z19C frame header 0xFF. "
                "Check wiring: ESP TX->sensor Rx, ESP RX<-sensor Tx, common GND."
            )
        else:
            summary = "MH-Z19C header 0xFF detected in RX data"

        return {
            "byte_count": len(buffer),
            "has_mhz19_header": has_ff,
            "looks_like_pms5003": looks_like_pms,
            "first_bytes": [hex(b) for b in buffer[:8]],
            "summary": summary
        }

