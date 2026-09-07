import logging
from socket import (
    AF_INET,
    SOCK_STREAM,
    SO_REUSEADDR,
    SOL_SOCKET,
    timeout as SocketTimeout,
    socket,
)
from typing import Optional, Union

logger = logging.getLogger("ammeter_test")


class AmmeterClientError(Exception):
    """Raised when an ammeter measurement cannot be completed."""


class AmmeterTimeoutError(AmmeterClientError):
    """Raised when the socket connect/recv times out."""


class AmmeterEmptyResponseError(AmmeterClientError):
    """Raised when the ammeter closes the connection without sending data."""


class AmmeterInvalidResponseError(AmmeterClientError):
    """Raised when the payload cannot be parsed as a float."""


class AmmeterClient:
    """Unified TCP client for Greenlee, ENTES, and CIRCUTOR emulators."""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_TIMEOUT_S = 5.0
    DEFAULT_RETRIES = 2

    def __init__(
        self,
        name: str,
        port: int,
        command: Union[str, bytes],
        host: str = DEFAULT_HOST,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retries: int = DEFAULT_RETRIES,
    ):
        self.name = name
        self.port = int(port)
        self.host = host
        self.timeout_s = timeout_s
        self.retries = retries
        self.command = command.encode("utf-8") if isinstance(command, str) else command

    def measure(self) -> float:
        """Request one current reading, retrying transient socket errors."""
        last_error: Optional[AmmeterClientError] = None
        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return self._measure_once()
            except AmmeterClientError as exc:
                last_error = exc
                logger.warning(
                    "%s measurement attempt %s/%s failed: %s",
                    self.name,
                    attempt,
                    attempts,
                    exc,
                )

        raise last_error or AmmeterClientError(
            f"Failed to read current from {self.name} at {self.host}:{self.port}."
        )

    def _measure_once(self) -> float:
        try:
            with socket(AF_INET, SOCK_STREAM) as sock:
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.settimeout(self.timeout_s)
                sock.connect((self.host, self.port))
                sock.sendall(self.command)
                payload = sock.recv(1024)
        except SocketTimeout as exc:
            raise AmmeterTimeoutError(
                f"Timed out after {self.timeout_s}s waiting for {self.name} "
                f"at {self.host}:{self.port}."
            ) from exc
        except OSError as exc:
            raise AmmeterClientError(
                f"Socket error reading {self.name} at {self.host}:{self.port}: {exc}"
            ) from exc

        if not payload:
            raise AmmeterEmptyResponseError(
                f"No data received from {self.name} on port {self.port}."
            )

        try:
            text = payload.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise AmmeterInvalidResponseError(
                f"Non-UTF8 payload from {self.name}: {payload!r}"
            ) from exc

        if not text:
            raise AmmeterEmptyResponseError(
                f"Empty payload from {self.name} on port {self.port}."
            )

        try:
            return float(text)
        except ValueError as exc:
            raise AmmeterInvalidResponseError(
                f"Unexpected non-float response from {self.name}: {text!r}"
            ) from exc
