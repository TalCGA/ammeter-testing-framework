import statistics
from typing import Dict, List


class AnalysisError(Exception):
    """Raised when statistical metrics cannot be computed."""


class AnalysisEngine:
    """Compute required statistical metrics from collected current samples."""

    def compute(self, samples: List[Dict[str, float]]) -> Dict[str, float]:
        values = [float(sample["current_a"]) for sample in samples]
        if not values:
            raise AnalysisError("Cannot compute metrics for an empty sample set.")

        return {
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) >= 2 else 0.0,
            "min": min(values),
            "max": max(values),
            "sample_count": len(values),
        }
