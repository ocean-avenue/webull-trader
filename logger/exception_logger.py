from webull_trader.models import ExceptionLog


def log(exception: str, traceback: str, log_text: str):
    log = ExceptionLog(
        exception=exception,
        traceback=traceback,
        log_text=log_text,
    )
    log.save()