import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.utils.paths import dated_subdirectory, resolve_base_dir

_LOGGER_NAME = "ammeter_test"


def setup_logging(
    test_name: str = "ammeter_test",
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """Configure a shared logger that writes to the console and results/logs/YYYY-MM-DD/."""
    if log_dir:
        directory = Path(log_dir)
        if not directory.is_absolute():
            directory = dated_subdirectory(resolve_base_dir(log_dir, "results/logs"))
        else:
            directory.mkdir(parents=True, exist_ok=True)
    else:
        directory = dated_subdirectory(resolve_base_dir(None, "results/logs"))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = directory / f"{timestamp}_{test_name}.log"

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.debug("Logging initialized. File: %s", log_file)
    return logger


class TestLogger:
    """Thin wrapper around the shared ammeter test logger."""

    def __init__(self, test_name: str = "ammeter_test", log_dir: Optional[str] = None):
        self._test_name = test_name
        self.logger = setup_logging(test_name=test_name, log_dir=log_dir)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)
