import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ammeter_test")


class VisualizationError(Exception):
    """Raised when a measurement plot cannot be created."""


def plot_current_timeseries(
    devices: Dict[str, Dict[str, Any]],
    output_path: Path,
    title: str = "Ammeter current samples",
) -> Optional[str]:
    """Save a time-series PNG comparing successful ammeter runs."""
    series = []
    for name, device in devices.items():
        if device.get("status") != "ok":
            continue
        samples = device.get("samples") or []
        if not samples:
            continue
        series.append(
            (
                name,
                [float(sample["elapsed_s"]) for sample in samples],
                [float(sample["current_a"]) for sample in samples],
            )
        )

    if not series:
        logger.warning("Skipping plot: no successful sample series to visualize.")
        return None

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise VisualizationError(
            "matplotlib is required for plots. Install it with: pip install matplotlib"
        ) from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (absolute_ax, normalized_ax) = plt.subplots(
        nrows=2,
        ncols=1,
        sharex=True,
        figsize=(11, 8),
        constrained_layout=True,
    )
    fig.suptitle(title, fontsize=13)

    for name, elapsed, currents in series:
        absolute_ax.plot(elapsed, currents, marker="o", linewidth=1.5, label=name)
        mean = sum(currents) / len(currents)
        if mean:
            normalized = [value / mean for value in currents]
        else:
            normalized = currents
        normalized_ax.plot(elapsed, normalized, marker="o", linewidth=1.5, label=name)

    absolute_ax.set_ylabel("Current (A)")
    absolute_ax.set_yscale("log")
    absolute_ax.grid(True, which="both", linestyle="--", alpha=0.4)
    absolute_ax.legend(loc="best")
    absolute_ax.set_title("Absolute current (log scale)")

    normalized_ax.set_xlabel("Elapsed time (s)")
    normalized_ax.set_ylabel("Current / device mean")
    normalized_ax.axhline(1.0, color="black", linewidth=0.8, linestyle=":")
    normalized_ax.grid(True, linestyle="--", alpha=0.4)
    normalized_ax.legend(loc="best")
    normalized_ax.set_title("Shape comparison (normalized to each device mean)")

    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved comparison plot to %s", output_path)
    return str(output_path)
