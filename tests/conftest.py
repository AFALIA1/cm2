from __future__ import annotations

import pytest

from cm2 import storage


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "BASE_DIR", tmp_path)
    monkeypatch.setattr(storage, "CAMERAS_FILE", tmp_path / "cameras.json")
    monkeypatch.setattr(storage, "STREAMS_FILE", tmp_path / "streams.json")
    monkeypatch.setattr(storage, "BRANDS_FILE", tmp_path / "brands.yaml")
    monkeypatch.setattr(storage, "STREAM_WORKDIRS_DIR", tmp_path / "streams")
    monkeypatch.setattr(storage, "LOCK_FILE", tmp_path / ".lock")
    return tmp_path
