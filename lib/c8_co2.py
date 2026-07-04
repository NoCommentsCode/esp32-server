import time


class C8CO2:
    """
    Драйвер CO2-датчика C8 (HC8 / C8-CO2-5K).

    Pin-compatible с MH-Z19, но другой UART-протокол:
    - active: каждую 1 с шлёт 16 байт, заголовок 0x42 0x4D
    - query: команда 64 69 03 5E 4E, ответ 14 байт
    """

    ACTIVE_FRAME_LEN = 16
    QUERY_RESPONSE_LEN = 14
    QUERY_CMD = bytes([0x64, 0x69, 0x03, 0x5E, 0x4E])

    def __init__(self, uart, mode="active"):
        self.uart = uart
        self.mode = mode
        self.last_raw_response = None
        self.last_rx_buffer = None

    def _flush(self):
        for _ in range(64):
            available = self.uart.any()
            if not available:
                break
            self.uart.read(available)

    @staticmethod
    def _active_checksum(frame):
        return sum(frame[0:15]) & 0xFF

    def _find_active_frame(self, buffer):
        limit = len(buffer) - 15
        for index in range(limit):
            if buffer[index] != 0x42 or buffer[index + 1] != 0x4D:
                continue

            frame = buffer[index:index + 16]
            if len(frame) < 16:
                continue

            if frame[15] != self._active_checksum(frame):
                continue

            return bytes(frame)

        return None

    def _collect_buffer(self, timeout_ms):
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
            time.sleep_ms(20)

        self.last_rx_buffer = [hex(b) for b in buffer]
        return buffer

    def read_co2_active(self, timeout_ms=2000):
        buffer = self._collect_buffer(timeout_ms)
        frame = self._find_active_frame(buffer)
        if frame is None:
            raise OSError("C8 active frame timeout")

        self.last_raw_response = frame
        co2 = frame[6] * 256 + frame[7]
        return co2, frame

    def read_co2_query(self, timeout_ms=2000):
        self._flush()
        self.uart.write(self.QUERY_CMD)
        time.sleep_ms(100)

        buffer = self._collect_buffer(timeout_ms)
        for index in range(len(buffer) - 13):
            if buffer[index] != 0x64 or buffer[index + 1] != 0x69 or buffer[index + 2] != 0x03:
                continue

            frame = bytes(buffer[index:index + 14])
            if len(frame) < 14:
                continue

            self.last_raw_response = frame
            co2 = frame[5] * 256 + frame[4]
            return co2, frame

        raise OSError("C8 query response timeout")

    def read_co2(self):
        if self.mode == "query":
            co2, frame = self.read_co2_query()
            mode = "query"
        else:
            co2, frame = self.read_co2_active()
            mode = "active"

        return {
            "co2_ppm": co2,
            "raw": frame,
            "mode": mode
        }

    def sniff(self, wait_ms=500):
        return self._collect_buffer(wait_ms)

    @staticmethod
    def analyze_buffer(buffer):
        if not buffer:
            return {
                "byte_count": 0,
                "detected_protocol": None,
                "has_c8_active_header": False,
                "has_mhz19_header": False,
                "summary": "RX line is silent"
            }

        has_c8 = len(buffer) >= 2 and buffer[0] == 0x42 and buffer[1] == 0x4D
        has_mhz19 = 0xFF in buffer
        has_query = len(buffer) >= 3 and buffer[0] == 0x64 and buffer[1] == 0x69 and buffer[2] == 0x03

        if has_c8:
            detected = "c8_active"
            summary = "C8 sensor active mode frame detected (0x42 0x4D)"
        elif has_query:
            detected = "c8_query"
            summary = "C8 sensor query response detected (0x64 0x69 0x03)"
        elif has_mhz19:
            detected = "mhz19c"
            summary = "MH-Z19C frame header 0xFF detected"
        else:
            detected = None
            summary = "Unknown UART protocol on RX line"

        return {
            "byte_count": len(buffer),
            "detected_protocol": detected,
            "has_c8_active_header": has_c8,
            "has_mhz19_header": has_mhz19,
            "first_bytes": [hex(b) for b in buffer[:8]],
            "summary": summary
        }
