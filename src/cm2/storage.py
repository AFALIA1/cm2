from __future__ import annotations

import contextlib
import fcntl
import json
import os
import stat
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(os.environ.get("CM2_HOME", Path.home() / ".cm2"))
CAMERAS_FILE = BASE_DIR / "cameras.json"
STREAMS_FILE = BASE_DIR / "streams.json"
BRANDS_FILE = BASE_DIR / "brands.yaml"
STREAM_WORKDIRS_DIR = BASE_DIR / "streams"
LOCK_FILE = BASE_DIR / ".lock"


def ensure_base_dir() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_WORKDIRS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(BASE_DIR, stat.S_IRWXU)


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """Guards read-modify-write sequences across concurrent `cm2` invocations."""
    ensure_base_dir()
    fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _atomic_write_text(path: Path, text: str) -> None:
    ensure_base_dir()
    tmp_path = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp_path, "w") as f:
        f.write(text)
    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp_path, path)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_json_list(path: Path, items: list[dict[str, Any]]) -> None:
    _atomic_write_text(path, json.dumps(items, indent=2))


def write_text(path: Path, text: str) -> None:
    _atomic_write_text(path, text)
