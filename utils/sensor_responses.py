from models.response import HttpResponse


def sensor_not_configured(sensor_name):
    """Ответ для отключённого в config.py датчика."""
    return HttpResponse(
        status_code=404,
        error="{} not configured on this station".format(sensor_name)
    )
