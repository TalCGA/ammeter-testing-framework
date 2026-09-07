import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.utils.paths import dated_subdirectory, resolve_base_dir


class ResultArchiver:
    """Persist one unified JSON session report under results/runs/YYYY-MM-DD/."""

    def __init__(
        self,
        runs_dir: Optional[str] = None,
        plots_dir: Optional[str] = None,
    ):
        self.runs_base = resolve_base_dir(runs_dir, "results/runs")
        self.plots_base = resolve_base_dir(plots_dir, "results/plots")
        self.session_id: Optional[str] = None
        self.started_utc: Optional[datetime] = None
        self.runs_dir = None
        self.plots_dir = None
        self._sampling: Dict[str, Any] = {}
        self._session_metadata: Dict[str, Any] = {}
        self._devices: Dict[str, Any] = {}
        self._order: List[str] = []
        self._start_perf: Optional[float] = None

    @staticmethod
    def build_session_id(timestamp: datetime) -> str:
        utc = timestamp.astimezone(timezone.utc)
        return f"{utc.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4()}"

    def start_session(
        self,
        sampling: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        self.started_utc = datetime.now(timezone.utc)
        self._start_perf = time.perf_counter()
        self.session_id = self.build_session_id(self.started_utc)
        self.runs_dir = dated_subdirectory(self.runs_base, self.started_utc)
        self.plots_dir = dated_subdirectory(self.plots_base, self.started_utc)
        self._sampling = dict(sampling)
        self._session_metadata = dict(metadata or {})
        self._devices = {}
        self._order = []
        return self.session_id

    def add_device_result(
        self,
        ammeter_type: str,
        metadata: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
        samples: Optional[list] = None,
        status: str = "ok",
        error: Optional[str] = None,
    ) -> None:
        if self.session_id is None:
            raise RuntimeError("Call start_session() before adding device results.")

        self._order.append(ammeter_type)
        self._devices[ammeter_type] = {
            "status": status,
            "metadata": metadata,
            "metrics": metrics or {},
            "samples": samples or [],
            "error": error,
        }

    @property
    def devices(self) -> Dict[str, Any]:
        return self._devices

    def save_session(
        self,
        comparison: Optional[Dict[str, Any]] = None,
        plot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.session_id is None or self.started_utc is None or self.runs_dir is None:
            raise RuntimeError("Call start_session() before saving a session report.")

        finished_utc = datetime.now(timezone.utc)
        duration_s = (
            time.perf_counter() - self._start_perf if self._start_perf is not None else None
        )
        statuses = {
            name: device["status"] for name, device in self._devices.items()
        }
        report = {
            "session_id": self.session_id,
            "timestamp_utc": self.started_utc.isoformat(),
            "metadata": self._session_metadata,
            "sampling": self._sampling,
            "execution_summary": {
                "started_utc": self.started_utc.isoformat(),
                "finished_utc": finished_utc.isoformat(),
                "duration_s": duration_s,
                "ammeter_count": len(self._order),
                "ammeter_types": list(self._order),
                "statuses": statuses,
                "passed": sum(1 for status in statuses.values() if status == "ok"),
                "failed": sum(1 for status in statuses.values() if status != "ok"),
            },
            "comparison": comparison or {},
            "plot_path": plot_path,
            "devices": self._devices,
        }

        path = self.runs_dir / f"{self.session_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")

        report["archive_path"] = str(path)
        report["plots_dir"] = str(self.plots_dir)
        return report
