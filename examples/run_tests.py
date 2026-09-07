import argparse
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from src.testing.test_framework import AmmeterTestFramework

_EMULATOR_CLASSES = {
    "greenlee": GreenleeAmmeter,
    "entes": EntesAmmeter,
    "circutor": CircutorAmmeter,
}


def start_emulators(ammeters: dict) -> None:
    for name, spec in ammeters.items():
        cls = _EMULATOR_CLASSES[name]
        port = spec["port"]
        threading.Thread(target=lambda c=cls, p=port: c(p).start_server(), daemon=True).start()
    time.sleep(2)


def print_summary(report: dict) -> None:
    summary = report["execution_summary"]
    print(f"\nSession ID: {report['session_id']}")
    print(f"Archive:    {report['archive_path']}")
    if report.get("plot_path"):
        print(f"Plot:       {report['plot_path']}")
    print(
        f"Summary:    {summary['passed']} passed, {summary['failed']} failed "
        f"in {summary['duration_s']:.2f}s"
    )

    for ammeter_type, device in report["devices"].items():
        print(f"\nResults for {ammeter_type} ({device['status']}):")
        if device["status"] != "ok":
            print(f"  Error:     {device.get('error')}")
            continue
        metrics = device["metrics"]
        cv = metrics.get("coefficient_of_variation")
        cv_text = f"{cv:.4f}" if cv is not None else "n/a"
        print(f"  Samples:   {metrics['sample_count']}")
        print(f"  Mean:      {metrics['mean']:.6f} A")
        print(f"  Median:    {metrics['median']:.6f} A")
        print(f"  Std Dev:   {metrics['std_dev']:.6f} A")
        print(f"  Min:       {metrics['min']:.6f} A")
        print(f"  Max:       {metrics['max']:.6f} A")
        print(f"  CV:        {cv_text}")

    comparison = report.get("comparison") or {}
    if not comparison:
        return

    print("\nCross-ammeter comparison:")
    if comparison.get("note"):
        print(f"  Note: {comparison['note']}")
    if comparison.get("most_stable_ammeter"):
        print(f"  Most stable (lowest CV): {comparison['most_stable_ammeter']}")
    if comparison.get("reference_mean_a") is not None:
        print(f"  Reference mean (median of means): {comparison['reference_mean_a']:.6f} A")
    for pair_name, stats in (comparison.get("pairwise") or {}).items():
        ratio = stats.get("mean_ratio")
        ratio_text = f"{ratio:.4f}" if ratio is not None else "n/a"
        print(
            f"  {pair_name}: Δmean={stats['mean_difference_a']:.6f} A, "
            f"ratio={ratio_text}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ammeter sampling session.")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to YAML config (default: config/config.yaml)",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip matplotlib PNG generation for this session.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    framework = AmmeterTestFramework(
        config_path=args.config,
        enable_plot=False if args.no_plot else None,
    )
    start_emulators(framework.config["ammeters"])
    report = framework.run_session(["greenlee", "entes", "circutor"])
    print_summary(report)


if __name__ == "__main__":
    main()
