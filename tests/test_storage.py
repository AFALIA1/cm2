from __future__ import annotations

import stat

from cm2 import storage


def test_save_and_load_json_list_round_trip(isolated_home):
    items = [{"a": 1}, {"b": 2}]
    storage.save_json_list(storage.CAMERAS_FILE, items)
    assert storage.load_json_list(storage.CAMERAS_FILE) == items


def test_load_json_list_missing_file_returns_empty(isolated_home):
    assert storage.load_json_list(storage.CAMERAS_FILE) == []


def test_saved_file_is_user_only_permissions(isolated_home):
    storage.save_json_list(storage.CAMERAS_FILE, [{"x": 1}])
    mode = stat.S_IMODE(storage.CAMERAS_FILE.stat().st_mode)
    assert mode == stat.S_IRUSR | stat.S_IWUSR


def test_locked_context_manager_is_reentrant_safe(isolated_home):
    with storage.locked():
        storage.save_json_list(storage.STREAMS_FILE, [{"id": "1"}])
    with storage.locked():
        assert storage.load_json_list(storage.STREAMS_FILE) == [{"id": "1"}]
