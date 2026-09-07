import statistics

import pytest

from src.testing.analysis import AnalysisEngine, AnalysisError


def _samples(values):
    return [{"index": i, "elapsed_s": float(i), "current_a": value} for i, value in enumerate(values)]


def test_compute_known_dataset():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    metrics = AnalysisEngine().compute(_samples(values))
    expected_std = statistics.stdev(values)
    assert metrics["mean"] == pytest.approx(3.0)
    assert metrics["median"] == pytest.approx(3.0)
    assert metrics["std_dev"] == pytest.approx(expected_std)
    assert metrics["min"] == pytest.approx(1.0)
    assert metrics["max"] == pytest.approx(5.0)
    assert metrics["sample_count"] == 5
    assert metrics["coefficient_of_variation"] == pytest.approx(expected_std / 3.0)


def test_compute_single_sample_has_zero_std_dev():
    metrics = AnalysisEngine().compute(_samples([4.2]))
    assert metrics["mean"] == pytest.approx(4.2)
    assert metrics["median"] == pytest.approx(4.2)
    assert metrics["std_dev"] == 0.0
    assert metrics["coefficient_of_variation"] == pytest.approx(0.0)


def test_compute_empty_samples_raises():
    with pytest.raises(AnalysisError, match="empty"):
        AnalysisEngine().compute([])


def test_compare_devices_stability_and_ratios():
    engine = AnalysisEngine()
    stable = engine.compute(_samples([10.0, 10.2, 9.8, 10.1, 9.9]))
    noisy = engine.compute(_samples([1.0, 5.0, 9.0, 2.0, 8.0]))
    devices = {
        "stable": {"status": "ok", "metrics": stable, "samples": _samples([10.0, 10.2, 9.8, 10.1, 9.9])},
        "noisy": {"status": "ok", "metrics": noisy, "samples": _samples([1.0, 5.0, 9.0, 2.0, 8.0])},
        "failed": {"status": "error", "metrics": {}, "error": "timeout"},
    }

    comparison = engine.compare_devices(devices)
    assert comparison["most_stable_ammeter"] == "stable"
    assert comparison["stability_ranking_lowest_cv_first"][0] == "stable"
    assert "failed" not in comparison["relative_stability"]

    expected_reference = statistics.median([stable["mean"], noisy["mean"]])
    assert comparison["reference_mean_a"] == pytest.approx(expected_reference)
    pair = comparison["pairwise"]["stable_vs_noisy"]
    assert pair["mean_difference_a"] == pytest.approx(stable["mean"] - noisy["mean"])
    assert pair["mean_ratio"] == pytest.approx(stable["mean"] / noisy["mean"])


def test_compare_devices_requires_two_successes():
    comparison = AnalysisEngine().compare_devices(
        {
            "only": {
                "status": "ok",
                "metrics": {"mean": 1.0, "std_dev": 0.1, "min": 0.9, "max": 1.1},
            }
        }
    )
    assert comparison["available_devices"] == ["only"]
    assert "most_stable_ammeter" not in comparison
