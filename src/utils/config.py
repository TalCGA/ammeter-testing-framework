from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigError(Exception):
    """Raised when the YAML configuration cannot be loaded or is invalid."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_config_path(config_path: str) -> Path:
    path = Path(config_path)
    if path.is_file():
        return path.resolve()

    candidate = _repo_root() / config_path
    if candidate.is_file():
        return candidate.resolve()

    raise ConfigError(f"Configuration file not found: {config_path}")


def _require_mapping(value: Any, key: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"Expected '{key}' to be a mapping in the configuration file.")
    return value


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    testing = _require_mapping(config.get("testing"), "testing")
    sampling = _require_mapping(testing.get("sampling"), "testing.sampling")
    for key in ("measurements_count", "total_duration_seconds", "sampling_frequency_hz"):
        if key not in sampling:
            raise ConfigError(f"Missing sampling parameter: testing.sampling.{key}")

    ammeters = _require_mapping(config.get("ammeters"), "ammeters")
    if not ammeters:
        raise ConfigError("At least one ammeter must be defined under 'ammeters'.")

    for name, spec in ammeters.items():
        spec = _require_mapping(spec, f"ammeters.{name}")
        if "port" not in spec or "command" not in spec:
            raise ConfigError(f"Ammeter '{name}' must define 'port' and 'command'.")
        try:
            spec["port"] = int(spec["port"])
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"Ammeter '{name}' has an invalid port: {spec.get('port')}") from exc
        if not isinstance(spec["command"], str) or not spec["command"].strip():
            raise ConfigError(f"Ammeter '{name}' has an invalid command.")
        ammeters[name] = spec

    result_management = config.get("result_management") or {}
    if result_management is None:
        result_management = {}
    if not isinstance(result_management, dict):
        raise ConfigError("Expected 'result_management' to be a mapping.")
    result_management.setdefault("runs_directory", "results/runs")
    result_management.setdefault("logs_directory", "results/logs")
    result_management.setdefault("plots_directory", "results/plots")
    config["result_management"] = result_management
    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load and validate config/config.yaml (or an explicit path)."""
    resolved = _resolve_config_path(config_path or "config/config.yaml")
    try:
        with resolved.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {resolved}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Unable to read configuration file {resolved}: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ConfigError(f"Configuration file {resolved} must contain a YAML mapping at the root.")

    return _validate_config(loaded)
