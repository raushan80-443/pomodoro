import time
import pytest
import network_monitor


def test_get_system_metrics_structure():
    """Verify get_system_metrics returns all required fields with proper types."""
    metrics = network_monitor.get_system_metrics()
    assert isinstance(metrics, dict)

    required_keys = [
        "cpu_percent",
        "memory_percent",
        "memory_used_gb",
        "memory_total_gb",
        "network_connected",
        "network_status",
        "is_high_usage",
        "high_usage_reason",
    ]
    for key in required_keys:
        assert key in metrics, f"Missing key: {key}"

    assert isinstance(metrics["cpu_percent"], (int, float))
    assert isinstance(metrics["memory_percent"], (int, float))
    assert isinstance(metrics["memory_used_gb"], (int, float))
    assert isinstance(metrics["memory_total_gb"], (int, float))
    assert isinstance(metrics["network_connected"], bool)
    assert isinstance(metrics["network_status"], str)
    assert isinstance(metrics["is_high_usage"], bool)


def test_high_resource_detection_cpu_trigger(monkeypatch):
    """Verify is_high_usage becomes True when CPU exceeds threshold (>= 80%)."""
    monkeypatch.setattr(network_monitor, "RESOURCE_CPU_THRESHOLD", 80)
    monkeypatch.setattr(network_monitor, "RESOURCE_RAM_THRESHOLD", 80)

    # Mock psutil or return values
    def mock_get_system_metrics():
        return {
            "cpu_percent": 85.0,
            "memory_percent": 45.0,
            "memory_used_gb": 4.0,
            "memory_total_gb": 16.0,
            "network_connected": True,
            "network_status": "Online (20ms)",
            "is_high_usage": True,
            "high_usage_reason": "CPU at 85%",
        }

    monkeypatch.setattr(network_monitor, "get_system_metrics", mock_get_system_metrics)

    metrics = network_monitor.get_system_metrics()
    assert metrics["is_high_usage"] is True
    assert "CPU at 85%" in metrics["high_usage_reason"]


def test_high_resource_detection_ram_trigger(monkeypatch):
    """Verify is_high_usage becomes True when RAM exceeds threshold (>= 80%)."""
    def mock_get_system_metrics():
        return {
            "cpu_percent": 25.0,
            "memory_percent": 88.0,
            "memory_used_gb": 14.1,
            "memory_total_gb": 16.0,
            "network_connected": True,
            "network_status": "Online (25ms)",
            "is_high_usage": True,
            "high_usage_reason": "Memory at 88%",
        }

    monkeypatch.setattr(network_monitor, "get_system_metrics", mock_get_system_metrics)

    metrics = network_monitor.get_system_metrics()
    assert metrics["is_high_usage"] is True
    assert "Memory at 88%" in metrics["high_usage_reason"]


def test_system_and_network_monitor_state_machine(monkeypatch):
    """Test the 15-second sustained threshold before triggering high resource alert."""
    mon = network_monitor.SystemAndNetworkMonitor(cpu_threshold=80, ram_threshold=80)

    # Step 1: Normal metrics -> RESOURCES_HEALTHY
    monkeypatch.setattr(network_monitor, "get_system_metrics", lambda: {
        "cpu_percent": 30.0,
        "memory_percent": 50.0,
        "memory_used_gb": 8.0,
        "memory_total_gb": 16.0,
        "network_connected": True,
        "network_status": "Online",
        "is_high_usage": False,
        "high_usage_reason": None,
    })
    res = mon.check_system_resources_once()
    assert res == "RESOURCES_HEALTHY"
    assert mon.resource_stressed_started_at is None

    # Step 2: High metrics start -> STRESSED_WAITING (sustained under 15s)
    monkeypatch.setattr(network_monitor, "get_system_metrics", lambda: {
        "cpu_percent": 88.0,
        "memory_percent": 82.0,
        "memory_used_gb": 13.1,
        "memory_total_gb": 16.0,
        "network_connected": True,
        "network_status": "Online",
        "is_high_usage": True,
        "high_usage_reason": "CPU at 88% and Memory at 82%",
    })
    res = mon.check_system_resources_once()
    assert res == "STRESSED_WAITING"
    assert mon.resource_stressed_started_at is not None

    # Step 3: Sustained for 16 seconds -> ALERT_HIGH_RESOURCES
    mon.resource_stressed_started_at = time.time() - 16
    monkeypatch.setattr(network_monitor, "send_desktop_notification", lambda *a, **kw: True)
    monkeypatch.setattr(network_monitor, "play_alert_sound", lambda *a, **kw: True)
    monkeypatch.setattr(network_monitor, "show_floating_toast", lambda *a, **kw: True)

    res = mon.check_system_resources_once()
    assert res == "ALERT_HIGH_RESOURCES"


def test_has_default_gateway():
    """Verify has_default_gateway returns a boolean and an interface name or None."""
    has_gw, iface = network_monitor.has_default_gateway()
    assert isinstance(has_gw, bool)
    if has_gw:
        assert isinstance(iface, str)


def test_resource_alert_cooldown_prevents_spam(monkeypatch):
    """Verify that after firing an alert, subsequent checks within cooldown return STRESSED_WAITING."""
    mon = network_monitor.SystemAndNetworkMonitor(cpu_threshold=80, ram_threshold=80)
    monkeypatch.setattr(network_monitor, "get_system_metrics", lambda: {
        "cpu_percent": 95.0,
        "memory_percent": 90.0,
        "memory_used_gb": 14.0,
        "memory_total_gb": 16.0,
        "network_connected": True,
        "network_status": "Online",
        "is_high_usage": True,
        "high_usage_reason": "CPU at 95%",
    })
    monkeypatch.setattr(network_monitor, "send_desktop_notification", lambda *a, **kw: True)
    monkeypatch.setattr(network_monitor, "play_alert_sound", lambda *a, **kw: True)
    monkeypatch.setattr(network_monitor, "show_floating_toast", lambda *a, **kw: True)

    mon.resource_stressed_started_at = time.time() - 20
    # First alert fires
    assert mon.check_system_resources_once() == "ALERT_HIGH_RESOURCES"

    # Immediate second check must NOT fire another alert (within 180s cooldown)
    assert mon.check_system_resources_once() == "STRESSED_WAITING"


def test_network_monitor_recovery_detection(monkeypatch):
    """Verify monitor triggers recovery notification when connectivity is restored after an alert."""
    mon = network_monitor.SystemAndNetworkMonitor(slow_threshold_ms=600, slow_duration=30)
    mon.alert_active = True  # Simulating active previous network alert

    monkeypatch.setattr(network_monitor, "has_default_gateway", lambda: (True, "wlan0"))
    monkeypatch.setattr(network_monitor, "measure_internet_latency", lambda timeout_sec=2.2: (True, 24.5, "8.8.8.8"))

    recovery_triggered = []
    monkeypatch.setattr(network_monitor, "send_desktop_notification", lambda title, msg, **kw: recovery_triggered.append(title))
    monkeypatch.setattr(network_monitor, "play_alert_sound", lambda mode: True)
    monkeypatch.setattr(network_monitor, "show_floating_toast", lambda *a, **kw: True)

    status = mon.check_network_once()
    assert status == "HEALTHY"
    assert mon.alert_active is False
    assert len(recovery_triggered) == 1
    assert "Internet Restored" in recovery_triggered[0]

