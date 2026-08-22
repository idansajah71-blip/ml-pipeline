import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": "ml-pipeline-api",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord("", "", "", 0, "", (), None).__dict__
            and k not in ["message", "msg", "args", "exc_info", "exc_text", "stack_info", "created", "relativeCreated", "msecs", "thread", "threadName", "processName", "process", "name", "levelname", "filename", "module", "funcName", "lineno", "pathname", "levelname", "message"]
        }
        log_entry.update(extra_fields)

        return json.dumps(log_entry, default=str)


class RequestContextFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        if self.request_id:
            record.request_id = self.request_id
        if self.user_id:
            record.user_id = self.user_id
        return True


request_filter = RequestContextFilter()


def setup_logging(log_level: str = "INFO"):
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    root_logger.addFilter(request_filter)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


class Logger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra or {})

    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, kwargs)

    def info(self, message: str, **kwargs):
        self._log("INFO", message, kwargs)

    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, kwargs)

    def error(self, message: str, **kwargs):
        self._log("ERROR", message, kwargs)

    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, kwargs)

    def exception(self, message: str, **kwargs):
        self.logger.exception(message, extra=kwargs)

    def log_request(self, method: str, path: str, status_code: int, duration: float, **kwargs):
        self.info(
            f"{method} {path} {status_code} {duration:.3f}s",
            http_method=method,
            http_path=path,
            http_status_code=status_code,
            http_duration=duration,
            **kwargs,
        )

    def log_prediction(self, model_id: str, latency: float, success: bool, **kwargs):
        self.info(
            f"Prediction: model={model_id} latency={latency:.3f}s success={success}",
            ml_model_id=model_id,
            ml_prediction_latency=latency,
            ml_prediction_success=success,
            **kwargs,
        )

    def log_training(self, model_id: str, algorithm: str, duration: float, metrics: Dict, **kwargs):
        self.info(
            f"Training: model={model_id} algorithm={algorithm} duration={duration:.1f}s",
            ml_model_id=model_id,
            ml_algorithm=algorithm,
            ml_training_duration=duration,
            ml_metrics=metrics,
            **kwargs,
        )


def get_logger(name: str) -> Logger:
    return Logger(name)
