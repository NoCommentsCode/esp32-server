# wifi_manager.py
import gc
import network
import time
from config import Config

class WiFiManager:
    """Управление подключением к Wi-Fi"""
    
    def __init__(self):
        gc.collect()
        self.wlan = network.WLAN(network.STA_IF)
        self.is_connected = False
    
    def connect(self):
        """Подключение к Wi-Fi сети"""
        gc.collect()
        try:
            if self.wlan.active():
                self.wlan.active(False)
                time.sleep_ms(100)
        except OSError:
            pass

        gc.collect()
        self.wlan.active(True)
        
        if self.wlan.isconnected():
            self.is_connected = True
            return True
        
        print(f'Подключение к {Config.WIFI_SSID}...')
        self.wlan.connect(Config.WIFI_SSID, Config.WIFI_PASSWORD)
        
        timeout = Config.WIFI_TIMEOUT
        while not self.wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
        if self.wlan.isconnected():
            self.is_connected = True
            print(f'✅ Подключено! IP: {self.get_ip()}')
            return True
        else:
            print('❌ Ошибка подключения')
            return False
    
    def disconnect(self):
        """Отключение от Wi-Fi"""
        self.wlan.disconnect()
        self.wlan.active(False)
        self.is_connected = False
    
    def get_ip(self):
        """Получение IP адреса"""
        if self.is_connected:
            return self.wlan.ifconfig()[0]
        return None
    
    def get_mac(self):
        """Получение MAC адреса"""
        import ubinascii
        mac = self.wlan.config('mac')
        return ubinascii.hexlify(mac, ':').decode()
    
    def get_status(self):
        """Получение статуса подключения"""
        return {
            'connected': self.is_connected,
            'ip': self.get_ip(),
            'mac': self.get_mac() if self.is_connected else None
        }