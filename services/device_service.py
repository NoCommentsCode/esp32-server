# services/device_service.py
import gc
import os
import sys
import machine
import ubinascii
from config import Config


class DeviceService:
    """Сервис для работы с аппаратной частью"""
    
    def __init__(self, wifi_manager):
        self.wifi_manager = wifi_manager
    
    def get_device_info(self):
        """Получение полной информации об устройстве"""
        uname = os.uname()
        
        return {
            'chip': {
                'platform': sys.platform,
                'micropython_version': uname.release,
                'machine_model': uname.machine,
                'cpu_frequency_hz': machine.freq(),
                'cpu_cores': 2,
                'architecture': 'Xtensa LX6'
            },
            'memory': self._get_memory_info(),
            'filesystem': self._get_filesystem_info(),
            'network': self.wifi_manager.get_status(),
            'temperature': self._get_temperature()
        }

    def get_discovery_info(self):
        """Информация для идентификации станции в сети (GET /discovery)."""
        mac = None
        if self.wifi_manager.is_connected:
            mac = self.wifi_manager.get_mac()

        return {
            'device_type': Config.DEVICE_TYPE,
            'api_version': Config.API_VERSION,
            'station': {
                'id': Config.STATION_ID,
                'name': Config.STATION_NAME,
                'mac': mac
            },
            'capabilities': Config.get_capabilities(),
            'status': 'online' if self.wifi_manager.is_connected else 'offline'
        }

    def _get_memory_info(self):
        """Информация о памяти"""
        free_ram = gc.mem_free()
        alloc_ram = gc.mem_alloc()
        
        info = {
            'ram_free_bytes': free_ram,
            'ram_allocated_bytes': alloc_ram,
            'ram_total_bytes': free_ram + alloc_ram
        }
        
        # Flash память
        try:
            import esp
            flash_size = esp.flash_size()
            info['flash_size_bytes'] = flash_size
            info['flash_size_mb'] = flash_size // (1024 * 1024)
        except:
            pass
        
        return info
    
    def _get_filesystem_info(self):
        """Информация о файловой системе"""
        try:
            fs_stats = os.statvfs('/')
            block_size = fs_stats[0]
            total_blocks = fs_stats[2]
            free_blocks = fs_stats[3]
            
            total_size = block_size * total_blocks
            free_size = block_size * free_blocks
            
            return {
                'total_bytes': total_size,
                'free_bytes': free_size,
                'used_bytes': total_size - free_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'free_mb': round(free_size / (1024 * 1024), 2)
            }
        except:
            return None
    
    def _get_temperature(self):
        """Получение температуры чипа"""
        try:
            import esp32
            return esp32.raw_temperature()
        except:
            return None