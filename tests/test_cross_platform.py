import os
from pathlib import Path
import importlib
import pytest

pomopkg = importlib.import_module("__init__")


def test_lock_file_path_generation():
    """Verify lock file path resolves cleanly to a valid Path with parent created."""
    lock_path = pomopkg._lock_file_path()
    assert isinstance(lock_path, Path)
    assert lock_path.name == "pomodoro.lock"
    assert lock_path.parent.exists()


def test_single_instance_lock_acquisition_and_release(tmp_path, monkeypatch):
    """Verify single instance lock can be acquired and blocks duplicate instances."""
    test_lock = tmp_path / "test_pomodoro.lock"
    monkeypatch.setattr(pomopkg, "_lock_file_path", lambda: test_lock)

    lock_file = pomopkg.acquire_single_instance_lock()
    assert lock_file is not None

    # Duplicate acquisition while first lock is held must return None
    second_lock = pomopkg.acquire_single_instance_lock()
    assert second_lock is None

    # Releasing the lock enables subsequent acquisition
    lock_file.close()
    third_lock = pomopkg.acquire_single_instance_lock()
    assert third_lock is not None
    third_lock.close()



def test_windows_batch_files_exist():
    """Verify that all production Windows batch & runner files are present."""
    root = Path(__file__).resolve().parent.parent
    expected_files = [
        "run_pomodoro.bat",
        "run_pomodoro_silent.vbs",
        "install_autostart_windows.bat",
        "uninstall_autostart_windows.bat",
    ]
    for filename in expected_files:
        f = root / filename
        assert f.exists(), f"Missing Windows script: {filename}"
        assert f.stat().st_size > 0, f"Empty Windows script: {filename}"


def test_linux_installer_scripts_exist():
    """Verify Linux installer scripts are present and non-empty."""
    root = Path(__file__).resolve().parent.parent
    expected_files = [
        "install.sh",
        "uninstall.sh",
    ]
    for filename in expected_files:
        f = root / filename
        assert f.exists(), f"Missing Linux script: {filename}"
        assert f.stat().st_size > 0, f"Empty Linux script: {filename}"


def test_requirements_file_contains_core_dependencies():
    """Verify requirements.txt contains essential packages for production."""
    root = Path(__file__).resolve().parent.parent
    req_file = root / "requirements.txt"
    assert req_file.exists()
    content = req_file.read_text().lower()
    assert "pymongo" in content
    assert "psutil" in content
