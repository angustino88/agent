import pytest

from src.app.controller.activity import activity_monitor as module
from src.app.controller.activity.activity_monitor import ActivityMonitor
from src.app.model.types.activity_status import ActivityStatus
from src.app.model.types.remote_session import RemoteSession


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def env(monkeypatch):
    clock, cursor = Clock(), {"pos": (0, 0)}
    monkeypatch.setattr(module.time, "monotonic", clock)
    monkeypatch.setattr(module.pyautogui, "position", lambda: cursor["pos"], raising=False)
    monitor = ActivityMonitor()
    changes = []
    monitor.status_changed.connect(changes.append)
    return monitor, clock, cursor, changes


def session(maintenance=False):
    return RemoteSession("pc", "tech", "ann", "Ann", "", "", is_maintenance=maintenance)


def test_no_session_is_free(env):
    monitor, _, _, changes = env
    monitor.run()
    assert changes == [(ActivityStatus.FREE, 0)]


def test_idle_cursor_becomes_inactive_and_counts_inactive_time(env):
    monitor, clock, cursor, changes = env
    monitor.on_session_started(session())
    monitor.run()
    assert changes[-1][0] is ActivityStatus.ACTIVE
    for _ in range(90):
        clock.now += 1
        monitor.run()
    assert changes[-1][0] is ActivityStatus.INACTIVE
    assert monitor.inactive_seconds_total == pytest.approx(90)
    cursor["pos"] = (500, 500)
    clock.now += 1
    monitor.run()
    assert changes[-1][0] is ActivityStatus.ACTIVE


def test_admin_maintenance_session_is_maintaining(env):
    monitor, _, _, changes = env
    monitor.on_session_started(session(maintenance=True))
    monitor.run()
    assert changes == [(ActivityStatus.MAINTAINING, 0)]
