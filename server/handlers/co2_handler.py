import json
from models.response import HttpResponse
from utils.logger import logger
from utils.sensor_responses import sensor_not_configured


class CO2Handler:
    """Обработчик эндпоинтов для CO2-датчика (C8 / MH-Z19C)."""

    def __init__(self, co2_service):
        self.co2_service = co2_service

    def handle_get_sensor(self, request):
        """
        GET /sensor/co2 - получить концентрацию CO2

        Query параметры:
        - force=true : игнорировать кэш
        """
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            if self.co2_service is None:
                return sensor_not_configured('CO2')

            query = request.get("query", {})
            force = query.get("force", "").lower() == "true"

            data = self.co2_service.read(force=force)
            if data is None:
                return HttpResponse(
                    status_code=503,
                    data={
                        "error": "Failed to read from CO2 sensor",
                        "diagnostics": self.co2_service.get_diagnostics()
                    }
                )

            response_data = {
                "co2_ppm": data["co2_ppm"],
                "cached": data.get("cached", False),
                "mode": data.get("mode")
            }

            meta = {
                "sensor_type": self.co2_service.sensor_type.upper(),
                "uart_id": self.co2_service.uart_id,
                "tx_pin": self.co2_service.tx_pin,
                "rx_pin": self.co2_service.rx_pin,
                "timestamp": self.co2_service.last_read_time
            }

            return HttpResponse(
                status_code=200,
                data={"sensor": response_data, "meta": meta}
            )
        except Exception as e:
            logger.error("Error in CO2 handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_get_status(self, request):
        """GET /sensor/co2/status - статус CO2-датчика."""
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            if self.co2_service is None:
                return sensor_not_configured('CO2')

            query = request.get("query", {})
            probe = query.get("probe", "").lower() in ("1", "true", "yes")

            status = self.co2_service.get_status(probe=probe)
            return HttpResponse(
                status_code=200,
                data=status
            )
        except Exception as e:
            logger.error("Error in CO2 status handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_probe(self, request):
        """GET /sensor/co2/probe - диагностика UART."""
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            if self.co2_service is None:
                return sensor_not_configured('CO2')

            result = self.co2_service.probe()
            status_code = 200 if result.get("ok") else 503
            return HttpResponse(status_code=status_code, data=result)
        except Exception as e:
            logger.error("Error in CO2 probe handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_set_abc(self, request):
        """POST /sensor/co2/abc - ABC только для MH-Z19C."""
        try:
            if request.get("method") != "POST":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use POST"
                )

            if self.co2_service is None:
                return sensor_not_configured('CO2')

            if self.co2_service.sensor_type != "mhz19c":
                return HttpResponse(
                    status_code=400,
                    error="ABC is supported only for MH-Z19C sensor"
                )

            body = request.get("body", "{}")
            try:
                data = json.loads(body)
            except Exception:
                return HttpResponse(
                    status_code=400,
                    error="Invalid JSON body"
                )

            if "enabled" not in data:
                return HttpResponse(
                    status_code=400,
                    error="Missing required field: enabled"
                )

            enabled = bool(data["enabled"])
            if not self.co2_service.set_abc(enabled):
                return HttpResponse(
                    status_code=503,
                    error="Failed to set ABC on CO2 sensor"
                )

            return HttpResponse(
                status_code=200,
                data={"abc_enabled": enabled, "result": "success"}
            )
        except Exception as e:
            logger.error("Error in CO2 ABC handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )
