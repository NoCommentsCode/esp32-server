# ESP32 Weather Station API

Домашняя метеостанция на **ESP32** с прошивкой **MicroPython** и REST API для чтения датчиков и управления GPIO.

## Возможности

- HTTP REST API на порту 80
- Датчики окружающей среды:
  - **DHT22** — температура, влажность
  - **BMP280** — температура, давление (I2C)
  - **C8** или **MH-Z19C** — концентрация CO₂ (UART)
- Внешняя погода через [WeatherAPI](https://www.weatherapi.com/)
- Управление GPIO, настройки в `config.json`, диагностика системы

## Аппаратная схема

| Датчик | Интерфейс | Пины ESP32 |
|--------|-----------|------------|
| DHT22 | 1-Wire | GPIO 14 (DATA) |
| BMP280 | I2C | GPIO 21 (SDA), GPIO 22 (SCL) |
| OLED GMO09605 (SSD1306) | I2C (та же шина) | GPIO 21 (SDA), GPIO 22 (SCK/SCL) |
| C8 / MH-Z19C | UART 9600 | GPIO 17 (TX → Rx датчика), GPIO 16 (RX ← Tx датчика) |

**CO₂ датчик C8:** питание **5V**, общий GND с ESP32. В активном режиме шлёт кадры `0x42 0x4D` раз в секунду — TX ESP32 не обязателен.

## Быстрый старт

### 1. Прошивка MicroPython

Установите [MicroPython для ESP32](https://micropython.org/download/ESP32_GENERIC/) и загрузите файлы проекта на устройство (Pymakr, Thonny, `ampy`, `mpremote` и т.п.).

### 2. Конфигурация

Секреты (Wi-Fi, ключ WeatherAPI) хранятся в `.env` и **не попадают в git**.

```bash
copy .env.example .env          # Windows
python scripts/generate_secrets.py
```

Заполните `.env`:

```env
WIFI_SSID=your-network
WIFI_PASSWORD=your-password
WEATHER_API_KEY=your-key
```

Скрипт создаёт `secrets.py` — загрузите его на ESP32 вместе с остальными файлами проекта. Аппаратные настройки (пины, тип CO₂ и т.д.) по-прежнему в `config.py`.

### 3. Запуск

```python
import main
main.main()
```

Или положите вызов в `boot.py`. После подключения к Wi-Fi сервер стартует на `http://<IP>:80`. IP можно узнать из лога или через `GET /info`.

### 4. Проверка

```bash
curl http://192.168.1.100/health
curl http://192.168.1.100/sensor/dht
curl http://192.168.1.100/sensor/bmp280
curl http://192.168.1.100/sensor/co2
```

## Документация API

Полная спецификация в формате **OpenAPI 3.0**:

📄 [`docs/openapi.yaml`](docs/openapi.yaml)

### Как просмотреть

| Способ | Действие |
|--------|----------|
| [Swagger Editor](https://editor.swagger.io/) | File → Import file → `docs/openapi.yaml` |
| VS Code / Cursor | Расширение **OpenAPI (Swagger) Editor** |
| [Redocly](https://redocly.github.io/redoc/) | Вставить содержимое YAML |
| Postman | Import → OpenAPI 3.0 |

### Обзор эндпоинтов

#### Система

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Статус сервера, свободная память |
| POST | `/system/restart` | Перезагрузка ESP32 |
| GET | `/info` | Информация об устройстве и сети |
| GET | `/info/deep` | Расширенная диагностика |

#### Датчики

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/sensor/dht` | Температура и влажность (DHT22) |
| GET | `/sensor/dht/status` | Статус DHT22 |
| GET | `/sensor/bmp280` | Температура и давление |
| GET | `/sensor/bmp280/status` | Статус BMP280 |
| GET | `/sensor/co2` | CO₂ в ppm |
| GET | `/sensor/co2/status` | Статус CO₂ (`?probe=true` — UART-диагностика) |
| GET | `/sensor/co2/probe` | Диагностика UART линии |
| POST | `/sensor/co2/abc` | ABC калибровка (только MH-Z19C) |
| GET | `/sensors` | Агрегат (заглушка) |

> Эндпоинты `/sensor/mhz19c/*` — устаревшие алиасы для `/sensor/co2/*`.

**Query-параметр `force=true`** — принудительное чтение без кэша (где применимо).

#### GPIO

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/gpio` | Все пины (`?mode=in` / `?mode=out`) |
| GET | `/gpio/{pin}` | Один пин |
| POST | `/gpio/{pin}` | Установить `{"state": 0\|1}` |
| POST | `/gpio/batch` | Пакетная установка `{"pins": {"2": 1}}` |

#### Настройки и погода

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/settings` | Настройки из `config.json` |
| POST | `/settings` | Обновить настройки |
| DELETE | `/settings` | Сброс к умолчаниям |
| GET | `/weather` | Погода (`?force=true`) |
| POST | `/weather/refresh` | Обновить кэш погоды |

### Примеры ответов

**GET /sensor/co2**

```json
{
  "sensor": {
    "co2_ppm": 412,
    "cached": false,
    "mode": "active"
  },
  "meta": {
    "sensor_type": "C8",
    "uart_id": 2,
    "tx_pin": 17,
    "rx_pin": 16,
    "timestamp": 123456
  }
}
```

**GET /sensor/dht?force=true**

```json
{
  "sensor": {
    "temperature_celsius": 23.5,
    "temperature_fahrenheit": 74.3,
    "humidity_percent": 45.2,
    "cached": false
  },
  "meta": {
    "sensor_type": "DHT22",
    "pin": 14,
    "timestamp": 123456
  }
}
```

## Структура проекта

```
esp32-server/
├── main.py              # Точка входа, регистрация маршрутов
├── boot.py
├── config.py            # Пины, тип CO₂ датчика, таймауты
├── secrets.example.py   # Шаблон секретов для ESP32
├── .env.example         # Шаблон секретов для локальной разработки
├── wifi_manager.py
├── docs/
│   └── openapi.yaml     # Спецификация API
├── server/
│   ├── app.py           # HTTP-сервер
│   ├── router.py
│   └── handlers/        # Обработчики эндпоинтов
├── services/            # Бизнес-логика и драйверы датчиков
├── lib/                 # Низкоуровневые драйверы (bmp280, c8_co2, mhz19c)
├── models/              # HttpResponse и модели
└── utils/               # Логгер, валидаторы
```

## Архитектура

- **handlers** — только HTTP: парсинг запроса, формирование `HttpResponse`
- **services** — работа с датчиками, GPIO, хранилищем
- **lib** — протоколы UART/I2C
- **config.py** — единая точка конфигурации

Добавление нового эндпоинта: сервис → handler → регистрация в `main.py` → обновление `docs/openapi.yaml`.

## Конфигурация CO₂

```python
CO2_SENSOR_TYPE = 'c8'       # 'c8' или 'mhz19c'
CO2_UART_ID = 2
CO2_TX_PIN = 17
CO2_RX_PIN = 16
CO2_BAUDRATE = 9600
CO2_SWAP_TX_RX = False       # поменять TX/RX в коде
CO2_C8_MODE = 'active'       # 'active' или 'query'
```

| Тип | Протокол | Заголовок кадра |
|-----|----------|-----------------|
| C8 | 16 байт / 1 с или query | `0x42 0x4D` |
| MH-Z19C | Команда `FF 01 86...` | `0xFF` |

## Коды ответов

| Код | Значение |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос |
| 404 | Не найдено |
| 405 | Метод не поддерживается |
| 500 | Внутренняя ошибка |
| 503 | Датчик / внешний сервис недоступен |

## Лицензия

Проект для личного использования.
