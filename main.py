import argparse
import threading
import time

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from Ammeters.client import request_current_from_ammeter
from src.utils.config import load_config

_EMULATOR_CLASSES = {
    "greenlee": GreenleeAmmeter,
    "entes": EntesAmmeter,
    "circutor": CircutorAmmeter,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start ammeter emulators and request one current reading from each."
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to YAML config (default: config/config.yaml)",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Accepted for CLI compatibility. This smoke test does not generate plots.",
    )
    return parser.parse_args()


def start_emulators(ammeters: dict) -> None:
    for name, spec in ammeters.items():
        cls = _EMULATOR_CLASSES[name]
        port = spec["port"]
        threading.Thread(target=lambda c=cls, p=port: c(p).start_server(), daemon=True).start()
    time.sleep(2)


def request_all(ammeters: dict) -> None:
    for spec in ammeters.values():
        request_current_from_ammeter(spec["port"], spec["command"].encode("utf-8"))


if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config)
    if args.no_plot:
        print("Note: --no-plot has no effect on this smoke test (no plots are generated).")

    start_emulators(config["ammeters"])
    request_all(config["ammeters"])
