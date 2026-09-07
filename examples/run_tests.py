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


def start_emulators() -> None:
    threading.Thread(target=lambda: GreenleeAmmeter(5000).start_server(), daemon=True).start()
    threading.Thread(target=lambda: EntesAmmeter(5001).start_server(), daemon=True).start()
    threading.Thread(target=lambda: CircutorAmmeter(5002).start_server(), daemon=True).start()
    time.sleep(2)


def print_summary(report: dict) -> None:
    summary = report["execution_summary"]
    print(f"\nSession ID: {report['session_id']}")
    print(f"Archive:    {report['archive_path']}")
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
        print(f"  Samples:   {metrics['sample_count']}")
        print(f"  Mean:      {metrics['mean']:.6f} A")
        print(f"  Median:    {metrics['median']:.6f} A")
        print(f"  Std Dev:   {metrics['std_dev']:.6f} A")
        print(f"  Min:       {metrics['min']:.6f} A")
        print(f"  Max:       {metrics['max']:.6f} A")


def main() -> None:
    start_emulators()
    framework = AmmeterTestFramework()
    report = framework.run_session(["greenlee", "entes", "circutor"])
    print_summary(report)


if __name__ == "__main__":
    main()
