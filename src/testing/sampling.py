import logging
import time
from typing import Any, Dict, List, Optional

from src.testing.ammeter_client import AmmeterClient

logger = logging.getLogger("ammeter_test")


class SamplingConfigError(Exception):
    """Raised when sampling parameters cannot be resolved."""


class SamplingEngine:
    """Collect timed current samples using count, duration, and frequency."""

    def __init__(
        self,
        measurements_count: Optional[int] = None,
        total_duration_seconds: Optional[float] = None,
        sampling_frequency_hz: Optional[float] = None,
    ):
        self.count, self.duration_s, self.frequency_hz = self._resolve_parameters(
            measurements_count,
            total_duration_seconds,
            sampling_frequency_hz,
        )
        self.period_s = 1.0 / self.frequency_hz

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or value == "" or (isinstance(value, str) and value.strip().upper() == "NULL")

    @classmethod
    def _resolve_parameters(
        cls,
        measurements_count: Optional[int],
        total_duration_seconds: Optional[float],
        sampling_frequency_hz: Optional[float],
    ) -> tuple:
        count = None if cls._is_missing(measurements_count) else int(measurements_count)
        duration = None if cls._is_missing(total_duration_seconds) else float(total_duration_seconds)
        frequency = None if cls._is_missing(sampling_frequency_hz) else float(sampling_frequency_hz)

        provided = sum(value is not None for value in (count, duration, frequency))
        if provided < 2:
            raise SamplingConfigError(
                "At least two of measurements_count, total_duration_seconds, "
                "and sampling_frequency_hz must be set."
            )

        if frequency is None:
            if duration <= 0 or count <= 0:
                raise SamplingConfigError("Duration and measurement count must be positive.")
            frequency = count / duration
        if count is None:
            if duration <= 0 or frequency <= 0:
                raise SamplingConfigError("Duration and sampling frequency must be positive.")
            count = max(1, int(round(duration * frequency)))
        if duration is None:
            if count <= 0 or frequency <= 0:
                raise SamplingConfigError("Measurement count and sampling frequency must be positive.")
            duration = count / frequency

        if count <= 0 or duration <= 0 or frequency <= 0:
            raise SamplingConfigError("Sampling parameters must be positive.")

        expected_count = duration * frequency
        if abs(expected_count - count) > 1:
            logger.warning(
                "Sampling parameters are inconsistent (count=%s, duration=%ss, frequency=%sHz). "
                "Using measurement count and frequency for scheduling.",
                count,
                duration,
                frequency,
            )

        return int(count), float(duration), float(frequency)

    def as_dict(self) -> Dict[str, float]:
        return {
            "measurements_count": self.count,
            "total_duration_seconds": self.duration_s,
            "sampling_frequency_hz": self.frequency_hz,
            "period_seconds": self.period_s,
        }

    def collect(self, client: AmmeterClient) -> List[Dict[str, float]]:
        """Take scheduled samples from a single ammeter client."""
        samples: List[Dict[str, float]] = []
        start = time.perf_counter()

        for index in range(self.count):
            target = start + (index * self.period_s)
            remaining = target - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)

            elapsed = time.perf_counter() - start
            if elapsed > self.duration_s + (self.period_s / 2):
                logger.warning(
                    "Stopping %s sampling early at sample %s; duration %.3fs exceeded.",
                    client.name,
                    index,
                    elapsed,
                )
                break

            current = client.measure()
            sample_elapsed = time.perf_counter() - start
            samples.append(
                {
                    "index": index,
                    "elapsed_s": sample_elapsed,
                    "current_a": current,
                }
            )
            logger.debug(
                "%s sample %s: %.6f A (elapsed %.3fs)",
                client.name,
                index,
                current,
                sample_elapsed,
            )

        if not samples:
            raise SamplingConfigError(f"No samples were collected from {client.name}.")

        return samples
