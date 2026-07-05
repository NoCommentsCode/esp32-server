#!/usr/bin/env python3
"""Generate secrets.py from .env for ESP32 deployment."""

from pathlib import Path

SECRETS_KEYS = ('WIFI_SSID', 'WIFI_PASSWORD', 'WEATHER_API_KEY')


def parse_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, _, value = line.partition('=')
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    env_file = root / '.env'

    if not env_file.exists():
        raise SystemExit(
            'File .env not found. Copy .env.example to .env and fill in your values.'
        )

    env = parse_env(env_file)
    missing = [key for key in SECRETS_KEYS if not env.get(key)]
    if missing:
        raise SystemExit(f'Missing required variables in .env: {", ".join(missing)}')

    lines = [
        '# Auto-generated from .env — do not commit',
        '',
    ]
    for key in SECRETS_KEYS:
        lines.append(f'{key} = {env[key]!r}')

    output = root / 'secrets.py'
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Written {output}')


if __name__ == '__main__':
    main()
