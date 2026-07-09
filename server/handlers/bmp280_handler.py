from models.response import HttpResponse
from utils.logger import logger
from utils.sensor_responses import sensor_not_configured


class BMP280Handler:
    """Обработчик эндпоинтов для датчика BMP280."""

    def __init__(self, bmp280_service):
        self.bmp280_service = bmp280_service

    def handle_get_sensor(self, request):
        """
        GET /sensor/bmp280 - получить текущие показания BMP280

        Query параметры:
        - force=true : игнорировать кэш и читать датчик принудительно
        """
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            if self.bmp280_service is None:
                return sensor_not_configured('BMP280')

            query = request.get("query", {})
            force = query.get("force", "").lower() == "true"

            data = self.bmp280_service.read(force=force)
            if data is None:
                return HttpResponse(
                    status_code=503,
                    error="Failed to read from BMP280 sensor"
                )

            response_data = {
                "temperature_celsius": round(data["temperature"], 1),
                "pressure_hpa": round(data["pressure_hpa"], 1),
                "pressure_pa": round(data["pressure_pa"], 1),
                "pressure_mmhg": round(data["pressure_mmhg"], 1),
                "cached": data.get("cached", False)
            }

            meta = {
                "sensor_type": "BMP280",
                "i2c_id": self.bmp280_service.i2c_id,
                "address": self.bmp280_service.address,
                "timestamp": self.bmp280_service.last_read_time
            }

            return HttpResponse(
                status_code=200,
                data={"sensor": response_data, "meta": meta}
            )
        except Exception as e:
            logger.error("Error in BMP280 handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_get_status(self, request):
        """GET /sensor/bmp280/status - статус BMP280."""
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            if self.bmp280_service is None:
                return sensor_not_configured('BMP280')

            status = self.bmp280_service.get_status()
            return HttpResponse(
                status_code=200,
                data=status
            )
        except Exception as e:
            logger.error("Error in BMP280 status handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )
