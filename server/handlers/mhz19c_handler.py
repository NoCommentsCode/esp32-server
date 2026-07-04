import json
from models.response import HttpResponse
from utils.logger import logger


class MHZ19CHandler:
    """Обработчик эндпоинтов для датчика MH-Z19C."""

    def __init__(self, mhz19c_service):
        self.mhz19c_service = mhz19c_service

    def handle_get_sensor(self, request):
        """
        GET /sensor/mhz19c - получить текущую концентрацию CO2

        Query параметры:
        - force=true : игнорировать кэш и читать датчик принудительно
        """
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            query = request.get("query", {})
            force = query.get("force", "").lower() == "true"

            data = self.mhz19c_service.read(force=force)
            if data is None:
                return HttpResponse(
                    status_code=503,
                    data={
                        "error": "Failed to read from MH-Z19C sensor",
                        "diagnostics": self.mhz19c_service.get_diagnostics()
                    }
                )

            response_data = {
                "co2_ppm": data["co2_ppm"],
                "cached": data.get("cached", False)
            }

            meta = {
                "sensor_type": "MH-Z19C",
                "uart_id": self.mhz19c_service.uart_id,
                "tx_pin": self.mhz19c_service.tx_pin,
                "rx_pin": self.mhz19c_service.rx_pin,
                "timestamp": self.mhz19c_service.last_read_time
            }

            return HttpResponse(
                status_code=200,
                data={"sensor": response_data, "meta": meta}
            )
        except Exception as e:
            logger.error("Error in MH-Z19C handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_get_status(self, request):
        """GET /sensor/mhz19c/status - статус MH-Z19C."""
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            query = request.get("query", {})
            probe = query.get("probe", "").lower() in ("1", "true", "yes")

            status = self.mhz19c_service.get_status(probe=probe)
            return HttpResponse(
                status_code=200,
                data=status
            )
        except Exception as e:
            logger.error("Error in MH-Z19C status handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_probe(self, request):
        """GET /sensor/mhz19c/probe - диагностика UART линии."""
        try:
            if request.get("method") != "GET":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use GET"
                )

            result = self.mhz19c_service.probe()
            status_code = 200 if result.get("ok") else 503
            return HttpResponse(status_code=status_code, data=result)
        except Exception as e:
            logger.error("Error in MH-Z19C probe handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )

    def handle_set_abc(self, request):
        """
        POST /sensor/mhz19c/abc - включить/выключить ABC

        Body JSON:
        {"enabled": true}
        """
        try:
            if request.get("method") != "POST":
                return HttpResponse(
                    status_code=405,
                    error="Method not allowed. Use POST"
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
            if not self.mhz19c_service.set_abc(enabled):
                return HttpResponse(
                    status_code=503,
                    error="Failed to set ABC on MH-Z19C"
                )

            return HttpResponse(
                status_code=200,
                data={"abc_enabled": enabled, "result": "success"}
            )
        except Exception as e:
            logger.error("Error in MH-Z19C ABC handler: {}".format(e))
            return HttpResponse(
                status_code=500,
                error="Internal error: {}".format(e)
            )
