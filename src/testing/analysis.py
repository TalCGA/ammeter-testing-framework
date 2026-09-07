import statistics
from typing import Any, Dict, List


class AnalysisError(Exception):
    """Raised when statistical metrics cannot be computed."""


class AnalysisEngine:
    """Compute required statistical metrics from collected current samples."""

    def compute(self, samples: List[Dict[str, float]]) -> Dict[str, float]:
        values = [float(sample["current_a"]) for sample in samples]
        if not values:
            raise AnalysisError("Cannot compute metrics for an empty sample set.")

        std_dev = statistics.stdev(values) if len(values) >= 2 else 0.0
        mean = statistics.fmean(values)
        return {
            "mean": mean,
            "median": statistics.median(values),
            "std_dev": std_dev,
            "min": min(values),
            "max": max(values),
            "sample_count": len(values),
            "coefficient_of_variation": (std_dev / abs(mean)) if mean else None,
        }

    def compare_devices(self, devices: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Relative cross-ammeter comparison (emulators share no physical reference)."""
        successful = {
            name: device
            for name, device in devices.items()
            if device.get("status") == "ok" and device.get("metrics")
        }
        if len(successful) < 2:
            return {
                "note": "Need at least two successful ammeter runs to compare devices.",
                "available_devices": list(successful),
            }

        stability: Dict[str, Any] = {}
        means: Dict[str, float] = {}
        for name, device in successful.items():
            metrics = device["metrics"]
            mean = float(metrics["mean"])
            std_dev = float(metrics["std_dev"])
            means[name] = mean
            cv = metrics.get("coefficient_of_variation")
            if cv is None:
                cv = (std_dev / abs(mean)) if mean else None
            stability[name] = {
                "mean_a": mean,
                "std_dev_a": std_dev,
                "coefficient_of_variation": cv,
                "range_a": float(metrics["max"]) - float(metrics["min"]),
            }

        ranked = sorted(
            stability,
            key=lambda name: (
                float("inf")
                if stability[name]["coefficient_of_variation"] is None
                else stability[name]["coefficient_of_variation"]
            ),
        )
        reference_mean = statistics.median(means.values())

        pairwise: Dict[str, Any] = {}
        names = list(successful)
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                left_mean = means[left]
                right_mean = means[right]
                pairwise[f"{left}_vs_{right}"] = {
                    "mean_difference_a": left_mean - right_mean,
                    "mean_ratio": (left_mean / right_mean) if right_mean else None,
                }

        versus_reference = {}
        for name, mean in means.items():
            versus_reference[name] = {
                "mean_minus_reference_a": mean - reference_mean,
                "mean_to_reference_ratio": (mean / reference_mean) if reference_mean else None,
            }

        return {
            "note": (
                "Emulators generate independent synthetic currents and do not share a "
                "physical reference. Scores describe relative agreement and stability, "
                "not absolute accuracy against a calibrated source."
            ),
            "reference_method": "median of per-device mean currents",
            "reference_mean_a": reference_mean,
            "relative_stability": stability,
            "stability_ranking_lowest_cv_first": ranked,
            "most_stable_ammeter": ranked[0] if ranked else None,
            "pairwise": pairwise,
            "versus_reference": versus_reference,
        }
