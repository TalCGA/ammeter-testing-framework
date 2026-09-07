import textwrap

import pytest
import yaml

from src.utils.config import ConfigError, load_config


def _write_yaml(path, content: str):
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def _valid_config_text(**overrides) -> str:
    sampling = overrides.get(
        "sampling",
        {
            "measurements_count": 10,
            "total_duration_seconds": 5,
            "sampling_frequency_hz": 2,
        },
    )
    return f"""
    testing:
      sampling:
        measurements_count: {sampling['measurements_count']}
        total_duration_seconds: {sampling['total_duration_seconds']}
        sampling_frequency_hz: {sampling['sampling_frequency_hz']}
    ammeters:
      greenlee:
        port: 5000
        command: "MEASURE_GREENLEE -get_measurement"
    """


def test_load_project_config_yaml():
    config = load_config("config/config.yaml")
    assert "greenlee" in config["ammeters"]
    assert config["ammeters"]["greenlee"]["port"] == 5000
    assert config["ammeters"]["entes"]["port"] == 5001
    assert config["ammeters"]["circutor"]["port"] == 5002
    assert config["testing"]["sampling"]["measurements_count"] == 10


def test_missing_file_raises_config_error():
    with pytest.raises(ConfigError, match="not found"):
        load_config("config/does-not-exist.yaml")


def test_invalid_yaml_raises_config_error(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("ammeters: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(str(path))


def test_non_mapping_root_raises_config_error(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML mapping"):
        load_config(str(path))


def test_missing_sampling_keys_raise(tmp_path):
    path = _write_yaml(
        tmp_path / "no_sampling.yaml",
        """
        testing:
          sampling: {}
        ammeters:
          greenlee:
            port: 5000
            command: "MEASURE_GREENLEE -get_measurement"
        """,
    )
    with pytest.raises(ConfigError, match="Missing sampling parameter"):
        load_config(str(path))


def test_missing_ammeter_port_raises(tmp_path):
    path = _write_yaml(
        tmp_path / "no_port.yaml",
        """
        testing:
          sampling:
            measurements_count: 10
            total_duration_seconds: 5
            sampling_frequency_hz: 2
        ammeters:
          greenlee:
            command: "MEASURE_GREENLEE -get_measurement"
        """,
    )
    with pytest.raises(ConfigError, match="port"):
        load_config(str(path))


def test_invalid_port_raises(tmp_path):
    path = _write_yaml(
        tmp_path / "bad_port.yaml",
        """
        testing:
          sampling:
            measurements_count: 10
            total_duration_seconds: 5
            sampling_frequency_hz: 2
        ammeters:
          greenlee:
            port: not-a-number
            command: "MEASURE_GREENLEE -get_measurement"
        """,
    )
    with pytest.raises(ConfigError, match="invalid port"):
        load_config(str(path))


def test_result_management_defaults_are_filled(tmp_path):
    path = _write_yaml(tmp_path / "no_results.yaml", _valid_config_text())
    config = load_config(str(path))
    assert config["result_management"]["runs_directory"] == "results/runs"
    assert config["result_management"]["logs_directory"] == "results/logs"
    assert config["result_management"]["plots_directory"] == "results/plots"


def test_valid_temporary_config_round_trip(tmp_path):
    path = _write_yaml(tmp_path / "ok.yaml", _valid_config_text())
    config = load_config(str(path))
    assert config["ammeters"]["greenlee"]["command"] == "MEASURE_GREENLEE -get_measurement"
    dumped = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert dumped["testing"]["sampling"]["sampling_frequency_hz"] == 2
