from config import Config, MUTABLE_SETTINGS
from utils.logger import logger


class SettingsService:
    """Управление настройками станции через Config и config.json."""

    def __init__(self, services, config_file=None):
        self.services = services
        self.config_file = config_file or Config.CONFIG_FILE

    def get_settings(self):
        return {
            'settings': Config.get_mutable_settings(),
            'meta': Config.get_settings_meta()
        }

    def update_settings(self, updates):
        if not isinstance(updates, dict):
            return {
                'ok': False,
                'errors': {'_body': 'Expected JSON object'}
            }

        errors = {}
        pending = {}

        for key, value in updates.items():
            coerced, error = Config.coerce_setting(key, value)
            if error is not None:
                errors[key] = error
                continue

            current_value = getattr(Config, key)
            if current_value != coerced:
                pending[key] = coerced

        if errors:
            return {
                'ok': False,
                'errors': errors,
                'settings': Config.get_mutable_settings(),
                'meta': Config.get_settings_meta()
            }

        applied = []
        restart_required = []
        backup = {key: getattr(Config, key) for key in pending}
        for key, coerced in pending.items():
            setattr(Config, key, coerced)
            if MUTABLE_SETTINGS[key].get('runtime'):
                applied.append(key)
            else:
                restart_required.append(key)

        if applied or restart_required:
            if not Config.save_to_file(self.config_file):
                for key, old_value in backup.items():
                    setattr(Config, key, old_value)
                return {
                    'ok': False,
                    'errors': {'_save': 'Failed to save config to {}'.format(self.config_file)},
                    'settings': Config.get_mutable_settings(),
                    'meta': Config.get_settings_meta()
                }

        if applied:
            self.apply_runtime_settings()

        return {
            'ok': True,
            'applied': applied,
            'restart_required': restart_required,
            'settings': Config.get_mutable_settings(),
            'meta': Config.get_settings_meta()
        }

    def reset_settings(self):
        Config.reset_mutable_settings()
        saved = Config.save_to_file(self.config_file)
        self.apply_runtime_settings()
        return {
            'ok': saved,
            'applied': Config.get_settings_meta()['runtime_keys'],
            'restart_required': Config.get_settings_meta()['restart_required_keys'],
            'settings': Config.get_mutable_settings(),
            'meta': Config.get_settings_meta()
        }

    def apply_runtime_settings(self):
        """Применить runtime-настройки к уже запущенным сервисам."""
        poll = self.services.get('sensor_poll')
        if poll is not None:
            poll.interval_ms = Config.SENSOR_POLL_INTERVAL_MS
            poll.enabled = Config.SENSOR_POLL_ENABLED and Config.has_pollable_sensors()

        display = self.services.get('display')
        if display is not None:
            display.event_duration_ms = Config.DISPLAY_EVENT_DURATION_MS
            display.idle_refresh_ms = Config.DISPLAY_IDLE_REFRESH_MS

        weather = self.services.get('weather')
        if weather is not None:
            weather.city = Config.WEATHER_CITY
            weather.update_interval = Config.WEATHER_UPDATE_INTERVAL

        logger.debug(
            "Runtime settings applied: poll_enabled={}, poll_interval_ms={}".format(
                poll.enabled if poll is not None else None,
                poll.interval_ms if poll is not None else None
            )
        )
