import logging
import sys
from typing import Any

from loguru import logger

from app.core.config import Settings, settings


class InterceptHandler(logging.Handler):
    """Envía los logs del ecosistema estándar a Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _add_request_id(record: dict[str, Any]) -> None:
    record["extra"].setdefault("request_id", "-")


def setup_logging(current_settings: Settings = settings) -> None:
    logger.remove()

    common = {
        "level": current_settings.log_level.upper(),
        "backtrace": current_settings.environment == "development",
        "diagnose": current_settings.environment == "development",
        "enqueue": True,
        "colorize": sys.stdout.isatty() and not current_settings.log_json,
    }

    if current_settings.log_json:
        logger.add(
            sys.stdout,
            serialize=True,
            format="{message}",
            **common,
        )
    else:
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[request_id]}</cyan> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            **common,
        )

    if current_settings.log_file:
        logger.add(
            current_settings.log_file,
            rotation="10 MB",
            retention="14 days",
            compression="gz",
            serialize=current_settings.log_json,
            enqueue=True,
            level=current_settings.log_level.upper(),
            format="{time} | {level} | {extra[request_id]} | {message}",
        )

    logger.configure(patcher=_add_request_id)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi", "sqlalchemy", "slowapi"):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    logger.info(
        "Logging inicializado | environment={} | level={} | json={}",
        current_settings.environment,
        current_settings.log_level.upper(),
        current_settings.log_json,
    )


__all__ = ["InterceptHandler", "logger", "setup_logging"]
