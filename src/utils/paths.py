from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_base_dir(path_value: Optional[str], default_relative: str) -> Path:
    if path_value:
        directory = Path(path_value)
        return directory if directory.is_absolute() else repo_root() / directory
    return repo_root() / default_relative


def dated_subdirectory(base_dir: Path, when: Optional[datetime] = None) -> Path:
    """Return base_dir/YYYY-MM-DD using the UTC calendar date."""
    stamp = (when or datetime.now(timezone.utc)).astimezone(timezone.utc)
    directory = base_dir / stamp.strftime("%Y-%m-%d")
    directory.mkdir(parents=True, exist_ok=True)
    return directory
