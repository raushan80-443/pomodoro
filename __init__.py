from datetime import datetime, timezone
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
    from .pomo import run_break_session, run_work_session, wait_for_display
except Exception:
    # Fallback for running modules directly in development (python -c).
    from pomo import run_break_session, run_work_session, wait_for_display


ROOT_DIR = Path(__file__).resolve().parent
JSON_LOG_PATH = ROOT_DIR / "pomodoro_log.json"
ENV_PATHS = (ROOT_DIR / "env" / ".env", ROOT_DIR / ".env")
SESSION_COUNT = 3
WORK_TIME_SECONDS = 40 * 60
BREAK_TIME_SECONDS = 4 * 60
MONGO_COLLECTION_NAME = "pomodoro_sessions"


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


def load_json_log():
    if not JSON_LOG_PATH.exists():
        return {"appName": "pomodoro", "createdAt": iso_now(), "events": []}

    try:
        return json.loads(JSON_LOG_PATH.read_text())
    except json.JSONDecodeError:
        return {"appName": "pomodoro", "createdAt": iso_now(), "events": []}


def save_json_log(log_data):
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
        return

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        database = client[mongo_db_name]
        database[MONGO_COLLECTION_NAME].replace_one(
            {"sessionId": session_record["sessionId"]},
            session_record,
            upsert=True,
        )
    except PyMongoError as error:
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

    print("get some rest")
    break_result = run_break_session(
        break_seconds=break_seconds,
        default_next_work_seconds=WORK_TIME_SECONDS,
        default_next_break_seconds=BREAK_TIME_SECONDS,
    )

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
        "nextSessionWorkSeconds": break_result["nextWorkSeconds"],
        "nextSessionBreakSeconds": break_result["nextBreakSeconds"],
        "interactionLog": work_result["interactionLog"] + break_result["interactionLog"],
    }
    log_session(session_record)

    # If user hit Exit during the break, save and terminate the program.
    if break_result.get("exitApp"):
        print("Exit requested during break — saved session, quitting.")
        sync_pending_sessions()
        sys.exit(0)

    return {
        "nextWorkSeconds": break_result["nextWorkSeconds"],
        "nextBreakSeconds": break_result["nextBreakSeconds"],
    }


def main():
    load_environment()

    if env_flag("POMODORO_WAIT_FOR_DISPLAY", default=False):
        wait_for_display(
            initial_delay_seconds=env_int("POMODORO_DISPLAY_INITIAL_DELAY_SECONDS", 60),
            retry_seconds=env_int("POMODORO_DISPLAY_RETRY_SECONDS", 60),
        )

    sync_pending_sessions()

    next_work_override = None
    next_break_override = None

    for cycle_number in range(1, SESSION_COUNT + 1):
        work_seconds = next_work_override or WORK_TIME_SECONDS
        break_seconds = next_break_override or BREAK_TIME_SECONDS

        # Overrides are one-cycle only. They are reapplied only if user sets them
        # again in the current break screen.
        next_work_override = None
        next_break_override = None

        cycle_result = run_pomodoro_cycle(
            cycle_number=cycle_number,
            work_seconds=work_seconds,
            break_seconds=break_seconds,
        )

        next_work_seconds = cycle_result.get("nextWorkSeconds", WORK_TIME_SECONDS)
        next_break_seconds = cycle_result.get("nextBreakSeconds", BREAK_TIME_SECONDS)

        if next_work_seconds != WORK_TIME_SECONDS or next_break_seconds != BREAK_TIME_SECONDS:
            next_work_override = next_work_seconds
            next_break_override = next_break_seconds


if __name__ == "__main__":
    main()
