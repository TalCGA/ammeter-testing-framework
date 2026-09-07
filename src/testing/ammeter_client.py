from socket import AF_INET, SOCK_STREAM, SO_REUSEADDR, SOL_SOCKET, socket
from typing import Union


class AmmeterClientError(Exception):
    """Raised when an ammeter measurement cannot be completed."""


class AmmeterClient:
    """Unified TCP client for Greenlee, ENTES, and CIRCUTOR emulators."""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_TIMEOUT_S = 5.0

    def __init__(
        self,
        name: str,
        port: int,
        command: Union[str, bytes],
        host: str = DEFAULT_HOST,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ):
        self.name = name
        self.port = int(port)
        self.host = host
        self.timeout_s = timeout_s
        self.command = command.encode("utf-8") if isinstance(command, str) else command

    def measure(self) -> float:
        """Request one current reading and return it as a float (amperes)."""
        try:
            with socket(AF_INET, SOCK_STREAM) as sock:
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.settimeout(self.timeout_s)
                sock.connect((self.host, self.port))
                sock.sendall(self.command)
                payload = sock.recv(1024)
        except OSError as exc:
            raise AmmeterClientError(
                f"Failed to read current from {self.name} at {self.host}:{self.port}: {exc}"
            ) from exc

        if not payload:
            raise AmmeterClientError(
                f"No data received from {self.name} on port {self.port}."
            )

        text = payload.decode("utf-8").strip()
        try:
            return float(text)
        except ValueError as exc:
            raise AmmeterClientError(
                f"Invalid measurement from {self.name}: {text!r}"
            ) from exc
