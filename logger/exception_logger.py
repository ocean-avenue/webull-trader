import traceback
from webull_trader.models import ExceptionLog


def log(exception: str, log_text: str):
    log = ExceptionLog(
        exception=exception,
        traceback=traceback.format_exc(),
        log_text=log_text,
    )
    log.save()
