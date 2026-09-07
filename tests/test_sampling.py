import pytest

from src.testing.sampling import SamplingConfigError, SamplingEngine


class MockAmmeter:
    def __init__(self, readings, fail_on=None):
        self.name = "mock"
        self._readings = list(readings)
        self.fail_on = set(fail_on or [])
        self.calls = 0

    def measure(self):
        index = self.calls
        self.calls += 1
        if index in self.fail_on:
            raise TimeoutError("simulated socket timeout")
        if not self._readings:
            raise RuntimeError("no mock readings left")
        return self._readings.pop(0)


def test_resolve_missing_count_from_duration_and_frequency():
    engine = SamplingEngine(
        measurements_count=None,
        total_duration_seconds=2,
        sampling_frequency_hz=5,
    )
    assert engine.count == 10
    assert engine.frequency_hz == pytest.approx(5.0)
    assert engine.period_s == pytest.approx(0.2)


def test_resolve_missing_frequency_from_count_and_duration():
    engine = SamplingEngine(
        measurements_count=8,
        total_duration_seconds=2,
        sampling_frequency_hz=None,
    )
    assert engine.frequency_hz == pytest.approx(4.0)


def test_resolve_requires_at_least_two_parameters():
    with pytest.raises(SamplingConfigError, match="At least two"):
        SamplingEngine(measurements_count=10)


def test_collect_returns_mock_readings(monkeypatch):
    monkeypatch.setattr("src.testing.sampling.time.sleep", lambda _seconds: None)
    engine = SamplingEngine(
        measurements_count=4,
        total_duration_seconds=4,
        sampling_frequency_hz=1000,
    )
    client = MockAmmeter([1.1, 2.2, 3.3, 4.4])
    samples = engine.collect(client)

    assert [sample["current_a"] for sample in samples] == [1.1, 2.2, 3.3, 4.4]
    assert [sample["index"] for sample in samples] == [0, 1, 2, 3]
    assert all("elapsed_s" in sample for sample in samples)
    assert client.calls == 4


def test_collect_skips_failed_measurements(monkeypatch):
    monkeypatch.setattr("src.testing.sampling.time.sleep", lambda _seconds: None)
    engine = SamplingEngine(
        measurements_count=3,
        total_duration_seconds=3,
        sampling_frequency_hz=1000,
    )
    client = MockAmmeter([10.0, 30.0], fail_on={1})
    samples = engine.collect(client)

    assert [sample["current_a"] for sample in samples] == [10.0, 30.0]
    assert client.calls == 3


def test_collect_raises_when_all_measurements_fail(monkeypatch):
    monkeypatch.setattr("src.testing.sampling.time.sleep", lambda _seconds: None)
    engine = SamplingEngine(
        measurements_count=2,
        total_duration_seconds=2,
        sampling_frequency_hz=1000,
    )
    client = MockAmmeter([], fail_on={0, 1})
    with pytest.raises(SamplingConfigError, match="No samples were collected"):
        engine.collect(client)
