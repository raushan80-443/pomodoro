from datetime import datetime, timezone
import atexit
import fcntl
import json
import os
from pathlib import Path
import time
from uuid import uuid4
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError

try:
    # When run as a package (python -m pomodoro) use a relative import.
    from .pomo import run_break_session, run_work_session, wait_for_display, play_beep, _load_summary_stats
except Exception:
    # Fallback for running modules directly in development (python -c).
    from pomo import run_break_session, run_work_session, wait_for_display, play_beep, _load_summary_stats


ROOT_DIR = Path(__file__).resolve().parent
JSON_LOG_PATH = ROOT_DIR / "pomodoro_log.json"
ENV_PATHS = (ROOT_DIR / "env" / ".env", ROOT_DIR / ".env")
WORK_TIME_SECONDS = 40 * 60
BREAK_TIME_SECONDS = 4 * 60
MONGO_COLLECTION_NAME = "pomodoro_sessions"
LOCK_FILE_NAME = "pomodoro.lock"


def load_env_file(env_path):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")
        current_value = os.environ.get(normalized_key)

        if current_value is None or (
            "<db_password>" in current_value and "<db_password>" not in normalized_value
        ):
            os.environ[normalized_key] = normalized_value


def load_environment():
    for env_path in ENV_PATHS:
        load_env_file(env_path)


def iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _lock_file_path():
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if cache_home:
        lock_dir = Path(cache_home) / "pomodoro"
    else:
        lock_dir = Path.home() / ".cache" / "pomodoro"

    try:
        lock_dir.mkdir(parents=True, exist_ok=True)
        return lock_dir / LOCK_FILE_NAME
    except Exception:
        fallback_dir = Path("/tmp") / f"pomodoro-{os.getuid()}"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / LOCK_FILE_NAME


def acquire_single_instance_lock():
    lock_path = _lock_file_path()
    lock_file = open(lock_path, "w")

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return None

    lock_file.seek(0)
    lock_file.truncate()
    lock_file.write(str(os.getpid()))
    lock_file.flush()

    def _release_lock():
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            lock_file.close()
        except Exception:
            pass

    atexit.register(_release_lock)
    return lock_file


def load_json_log():
    if not JSON_LOG_PATH.exists():
        return {"appName": "pomodoro", "createdAt": iso_now(), "events": []}

    try:
        return json.loads(JSON_LOG_PATH.read_text())
    except json.JSONDecodeError:
        return {"appName": "pomodoro", "createdAt": iso_now(), "events": []}


def save_json_log(log_data):
    temp_path = JSON_LOG_PATH.with_suffix(".json.tmp")
    try:
        temp_path.write_text(json.dumps(log_data, indent=2))
        os.replace(temp_path, JSON_LOG_PATH)
    except Exception:
        JSON_LOG_PATH.write_text(json.dumps(log_data, indent=2))


def write_json_log(session_record):
    log_data = load_json_log()
    session_record = dict(session_record)
    session_record["syncStatus"] = "pending"
    log_data.setdefault("events", []).append(session_record)
    save_json_log(log_data)


def get_pending_sessions(log_data):
    return [event for event in log_data.get("events", []) if event.get("syncStatus") != "synced"]


def mark_sessions_synced(session_ids):
    if not session_ids:
        return

    log_data = load_json_log()
    updated_events = []
    session_id_set = set(session_ids)

    for event in log_data.get("events", []):
        updated_event = dict(event)
        if updated_event.get("sessionId") in session_id_set:
            updated_event["syncStatus"] = "synced"
        updated_events.append(updated_event)

    log_data["events"] = updated_events
    save_json_log(log_data)


def push_to_mongo(session_record):
    mongo_uri = os.environ.get("MONGODB_URI", "").strip()
    mongo_db_name = os.environ.get("MONGODB_DB", "todoApp").strip()

    if not mongo_uri or "<db_password>" in mongo_uri:
        print("MongoDB URI is missing or still uses <db_password>; saved locally only.")
        return False

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        database = client[mongo_db_name]
        database[MONGO_COLLECTION_NAME].replace_one(
            {"sessionId": session_record["sessionId"]},
            session_record,
            upsert=True,
        )
    except Exception as error:
        print(f"MongoDB write failed: {error}")
        return False
    finally:
        client.close()

    return True


def sync_pending_sessions():
    log_data = load_json_log()
    pending_sessions = get_pending_sessions(log_data)

    if not pending_sessions:
        return

    synced_session_ids = []
    for session_record in pending_sessions:
        if push_to_mongo(session_record):
            synced_session_ids.append(session_record["sessionId"])
        else:
            break

    mark_sessions_synced(synced_session_ids)


def log_session(session_record):
    write_json_log(session_record)
    sync_pending_sessions()


def run_pomodoro_cycle(cycle_number, work_seconds, break_seconds):
    session_started_at = iso_now()
    print(f"hold push your limit {cycle_number}")
    work_result = run_work_session(work_seconds)

    if not work_result.get("guiAvailable", False):
        print("GUI was not available for the work session; stopping pomodoro entirely.")
        return True

    if work_result.get("sessionInterruptedBySleep"):
        print("System sleep detected during work; saving the session and starting a fresh cycle.")
        session_record = {
            "sessionId": str(uuid4()),
            "cycle": cycle_number,
            "sessionStartedAt": session_started_at,
            "sessionCompletedAt": iso_now(),
            "workTimeMinutes": round(work_result["actualWorkSeconds"] / 60, 2),
            "workTimeSeconds": work_result["actualWorkSeconds"],
            "breakTimeMinutes": 0,
            "breakTimeSeconds": 0,
            "plannedWorkSeconds": work_result["plannedWorkSeconds"],
            "plannedBreakSeconds": 0,
            "workEndedBy": work_result["workEndedBy"],
            "breakEndedBy": "notStarted",
            "interactionLog": work_result["interactionLog"],
            "productivityRating": 0,
            "sessionInterruptedBySleep": True,
        }
        log_session(session_record)
        return None

    print("get some rest")
    stats = _load_summary_stats(current_work_seconds=work_result.get("actualWorkSeconds", 0))
    break_result = run_break_session(
        break_seconds=break_seconds,
        default_next_work_seconds=WORK_TIME_SECONDS,
        default_next_break_seconds=BREAK_TIME_SECONDS,
        stats=stats,
    )

    if break_result.get("sessionCanceled"):
        print("Break session could not start because GUI was unavailable; skipping log entry.")
        return None

    if break_result.get("sessionInterruptedBySleep"):
        print("System sleep detected during break; saving the session and starting a fresh cycle.")

    session_record = {
        "sessionId": str(uuid4()),
        "cycle": cycle_number,
        "sessionStartedAt": session_started_at,
        "sessionCompletedAt": iso_now(),
        "workTimeMinutes": round(work_result["actualWorkSeconds"] / 60, 2),
        "workTimeSeconds": work_result["actualWorkSeconds"],
        "breakTimeMinutes": round(break_result["actualBreakSeconds"] / 60, 2),
        "breakTimeSeconds": break_result["actualBreakSeconds"],
        "plannedWorkSeconds": work_result["plannedWorkSeconds"],
        "plannedBreakSeconds": break_result["plannedBreakSeconds"],
        "workEndedBy": work_result["workEndedBy"],
        "breakEndedBy": break_result["breakEndedBy"],
        # Removed nextSessionWorkSeconds/nextSessionBreakSeconds by design
        "interactionLog": work_result["interactionLog"] + break_result["interactionLog"],
            "productivityRating": break_result.get("productivityRating", 0),  # Default to 0 if not present
    }
    log_session(session_record)

    # If user hit Exit during the break, save and signal the caller to stop.
    if break_result.get("exitApp"):
        print("Exit requested during break — saved session, quitting.")
        sync_pending_sessions()
        return True

    # No return value needed; caller should not rely on nextWork/nextBreak values.
    return None


def main():
    load_environment()

    if len(sys.argv) > 1 and sys.argv[1] == "--test-sound":
        print("Playing test sound...")
        played = play_beep()
        if played:
            print("Sound play command triggered successfully.")
        else:
            print("Failed to play sound using any method.")
        return

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        print("Pomodoro is already running; skipping duplicate startup.")
        return

    session_count = max(1, env_int("POMODORO_SESSION_COUNT", 1))

    if env_flag("POMODORO_WAIT_FOR_DISPLAY", default=False):
        wait_for_display(
            initial_delay_seconds=env_int("POMODORO_DISPLAY_INITIAL_DELAY_SECONDS", 60),
            retry_seconds=env_int("POMODORO_DISPLAY_RETRY_SECONDS", 60),
        )

    sync_pending_sessions()

    next_work_override = None
    next_break_override = None

    for cycle_number in range(1, session_count + 1):
        work_seconds = next_work_override or WORK_TIME_SECONDS
        break_seconds = next_break_override or BREAK_TIME_SECONDS

        # Overrides are one-cycle only. They are reapplied only if user sets them
        # again in the current break screen.
        next_work_override = None
        next_break_override = None

        # run_pomodoro_cycle may return True to indicate the app should stop
        should_exit = run_pomodoro_cycle(
            cycle_number=cycle_number,
            work_seconds=work_seconds,
            break_seconds=break_seconds,
        )

        if should_exit:
            print("Shutdown requested; stopping pomodoro cycles.")
            return

        # There is no returned override from the cycle; use defaults.
        next_work_seconds = WORK_TIME_SECONDS
        next_break_seconds = BREAK_TIME_SECONDS


if __name__ == "__main__":
    main()
