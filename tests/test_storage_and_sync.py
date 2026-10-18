import json
import os
from pathlib import Path
from uuid import uuid4
import importlib
import pytest

pomopkg = importlib.import_module("__init__")


def test_load_json_log_missing_file(tmp_path, monkeypatch):
    """Verify loading from non-existent file returns default schema without crashing."""
    non_existent = tmp_path / "does_not_exist.json"
    monkeypatch.setenv("POMODORO_LOG_PATH", str(non_existent))

    data = pomopkg.load_json_log()
    assert data["appName"] == "pomodoro"
    assert "events" in data
    assert data["events"] == []


def test_load_json_log_corrupt_file(tmp_path, monkeypatch):
    """Verify loading from corrupt/invalid JSON returns default schema without crashing."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{this is not valid json!@@#}")
    monkeypatch.setenv("POMODORO_LOG_PATH", str(corrupt_file))

    data = pomopkg.load_json_log()
    assert data["appName"] == "pomodoro"
    assert data["events"] == []


def test_write_and_load_json_log(tmp_path, monkeypatch):
    """Verify write_json_log correctly appends session with pending sync status."""
    log_file = tmp_path / "sub" / "dir" / "test_log.json"
    monkeypatch.setenv("POMODORO_LOG_PATH", str(log_file))

    session_id = str(uuid4())
    record = {
        "sessionId": session_id,
        "cycle": 1,
        "workTimeMinutes": 40.0,
        "workTimeSeconds": 2400,
    }
    pomopkg.write_json_log(record)

    loaded = pomopkg.load_json_log()
    assert len(loaded["events"]) == 1
    saved = loaded["events"][0]
    assert saved["sessionId"] == session_id
    assert saved["syncStatus"] == "pending"


def test_get_pending_sessions():
    """Verify get_pending_sessions filters out already synced events."""
    log_data = {
        "appName": "pomodoro",
        "events": [
            {"sessionId": "1", "syncStatus": "synced"},
            {"sessionId": "2", "syncStatus": "pending"},
            {"sessionId": "3"},
        ],
    }
    pending = pomopkg.get_pending_sessions(log_data)
    assert len(pending) == 2
    assert [p["sessionId"] for p in pending] == ["2", "3"]


def test_mark_sessions_synced(tmp_path, monkeypatch):
    """Verify mark_sessions_synced updates the status of matching sessions."""
    log_file = tmp_path / "test_sync.json"
    monkeypatch.setenv("POMODORO_LOG_PATH", str(log_file))

    log_data = {
        "appName": "pomodoro",
        "events": [
            {"sessionId": "A", "syncStatus": "pending"},
            {"sessionId": "B", "syncStatus": "pending"},
        ],
    }
    pomopkg.save_json_log(log_data)

    pomopkg.mark_sessions_synced(["A"])

    reloaded = pomopkg.load_json_log()
    events_map = {e["sessionId"]: e["syncStatus"] for e in reloaded["events"]}
    assert events_map["A"] == "synced"
    assert events_map["B"] == "pending"


def test_push_to_mongo_graceful_missing_uri(monkeypatch):
    """Verify push_to_mongo fails safely and returns False when URI is placeholder or absent."""
    monkeypatch.setenv("MONGODB_URI", "")
    res = pomopkg.push_to_mongo({"sessionId": "test-123"})
    assert res is False

    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:<db_password>@cluster.mongodb.net/")
    res2 = pomopkg.push_to_mongo({"sessionId": "test-123"})
    assert res2 is False
