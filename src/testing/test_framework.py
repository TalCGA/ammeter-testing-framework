from typing import Any, Dict, Iterable, List, Optional

from src.testing.ammeter_client import AmmeterClient
from src.testing.analysis import AnalysisEngine
from src.testing.archive import ResultArchiver
from src.testing.sampling import SamplingEngine
from src.testing.visualization import VisualizationError, plot_current_timeseries
from src.utils.config import load_config
from src.utils.logger import setup_logging
from src.utils.paths import dated_subdirectory, resolve_base_dir


class AmmeterTestFramework:
    """Orchestrates sampling, analysis, and a single session archive."""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_config(config_path)
        result_dirs = self.config.get("result_management", {})
        logs_base = resolve_base_dir(result_dirs.get("logs_directory"), "results/logs")
        self.logger = setup_logging(log_dir=str(dated_subdirectory(logs_base)))

        sampling_cfg = self.config["testing"]["sampling"]
        self.sampling_engine = SamplingEngine(
            measurements_count=sampling_cfg.get("measurements_count"),
            total_duration_seconds=sampling_cfg.get("total_duration_seconds"),
            sampling_frequency_hz=sampling_cfg.get("sampling_frequency_hz"),
        )
        self.analysis_engine = AnalysisEngine()
        self.archiver = ResultArchiver(
            runs_dir=result_dirs.get("runs_directory"),
            plots_dir=result_dirs.get("plots_directory"),
        )

    def run_test(self, ammeter_type: str) -> Dict[str, Any]:
        ammeters = self.config["ammeters"]
        if ammeter_type not in ammeters:
            raise KeyError(
                f"Unknown ammeter '{ammeter_type}'. Configured types: {sorted(ammeters)}"
            )

        spec = ammeters[ammeter_type]
        client = AmmeterClient(
            name=ammeter_type,
            port=spec["port"],
            command=spec["command"],
        )
        self.logger.info(
            "Starting test for %s on %s:%s",
            ammeter_type,
            client.host,
            client.port,
        )

        samples = self.sampling_engine.collect(client)
        metrics = self.analysis_engine.compute(samples)
        self.logger.info(
            "%s metrics: mean=%.6f A median=%.6f A std_dev=%.6f A min=%.6f A max=%.6f A (n=%s)",
            ammeter_type,
            metrics["mean"],
            metrics["median"],
            metrics["std_dev"],
            metrics["min"],
            metrics["max"],
            metrics["sample_count"],
        )
        return {
            "ammeter_type": ammeter_type,
            "metadata": {
                "host": client.host,
                "port": client.port,
                "command": spec["command"],
            },
            "metrics": metrics,
            "samples": samples,
        }

    def run_session(self, ammeter_types: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        types: List[str] = list(ammeter_types or self.config["ammeters"].keys())
        session_id = self.archiver.start_session(
            sampling=self.sampling_engine.as_dict(),
            metadata={"config_ammeters": types},
        )
        self.logger.info("Started session %s for %s", session_id, types)

        for ammeter_type in types:
            try:
                result = self.run_test(ammeter_type)
                self.archiver.add_device_result(
                    ammeter_type=ammeter_type,
                    metadata=result["metadata"],
                    metrics=result["metrics"],
                    samples=result["samples"],
                    status="ok",
                )
            except Exception as exc:
                self.logger.exception("Test failed for %s", ammeter_type)
                spec = self.config["ammeters"].get(ammeter_type, {})
                self.archiver.add_device_result(
                    ammeter_type=ammeter_type,
                    metadata={
                        "host": "127.0.0.1",
                        "port": spec.get("port"),
                        "command": spec.get("command"),
                    },
                    status="error",
                    error=str(exc),
                )

        comparison = self.analysis_engine.compare_devices(self.archiver.devices)
        plot_path = self._maybe_plot()
        report = self.archiver.save_session(comparison=comparison, plot_path=plot_path)
        self.logger.info("Archived session report to %s", report["archive_path"])
        return report

    def _maybe_plot(self) -> Optional[str]:
        visualization_cfg = (self.config.get("analysis") or {}).get("visualization") or {}
        if visualization_cfg.get("enabled") is False:
            self.logger.info("Visualization disabled in config; skipping plot.")
            return None
        if self.archiver.plots_dir is None or self.archiver.started_utc is None:
            return None

        timestamp = self.archiver.started_utc.strftime("%Y%m%dT%H%M%SZ")
        output_path = self.archiver.plots_dir / f"run_{timestamp}_plot.png"
        try:
            return plot_current_timeseries(
                devices=self.archiver.devices,
                output_path=output_path,
                title=f"Ammeter current samples ({self.archiver.session_id})",
            )
        except VisualizationError as exc:
            self.logger.error("Could not generate plot: %s", exc)
            return None
