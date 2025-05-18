"""
Utilities for handling when the app goes offline.
"""

import datetime
import os
import json
import csv

import app.globals as globals
import app.utils.filesystem as filesystem
import app.utils.offline as offline

def write_poll_time():
    """
    Write the current timestamp to the last_poll file.
    Resilient to crashes and restarts.
    """
    timestamp = str(datetime.datetime.now(datetime.timezone.utc))
    tmp_file = f'{globals.LAST_POLL_FILE}.tmp'
    with open(tmp_file, 'w') as f:
        f.write(timestamp + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_file, globals.LAST_POLL_FILE)

def get_last_poll():
    """
    Read the last poll timestamp from file.
    If the file does not exist or is empty, returns 1 January 1970.
    """
    try:
        with open(globals.LAST_POLL_FILE, 'r') as f:
            return datetime.datetime.fromisoformat(f.readline().strip())
    except (FileNotFoundError, ValueError):
        return datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

def is_within_retention_period():
    """
    Check if the last poll time is within the queue retention period.
    """
    last_poll_time = get_last_poll()
    lower_bound = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=globals.QUEUE_RETENTION_DAYS)
    return last_poll_time >= lower_bound

def save_simple_fs_snapshot(out_file: str):
    """
    Creates a snapshot of the filesystem as a list of file paths.
    
    Format:
    ```
    <snapshot_timestamp>
    [file_path_1, ... file_path_n]
    ```
    """
    prefixes = [f"albums/{prefix}" for prefix in globals.ALLOWED_PREFIXES]
    file_paths = filesystem.list_files_in_dir(globals.BASE_DIR, prefixes)
    
    with open(out_file, 'w') as f:
        f.write(str(offline.get_last_poll()))
        f.write("\n")
        f.write(json.dumps(file_paths))

def save_offline_events(events_file: str, events: list[str]):
    with open(events_file, 'a') as f:
        for event in events:
            f.write(event + "\n")

def get_offline_events(events_file: str):
    events: list[dict[str, str]] = []
    if not os.path.exists(events_file):
        return events

    with open(events_file, 'r') as f:
        csv_file = csv.reader(f)
        for line in csv_file:
            if len(line) < 3:
                continue
            event = {'timestamp': line[0], 'event': line[1], 'path': line[2]}
            if line[1] == 'MOVE':
                event['newPath'] = line[3]
            events.append(event)
    return events

def clear_offline_events(events_file: str):
    if os.path.exists(events_file):
        with open(events_file, 'w') as file:
            pass

def get_snapshot_time():
    """
    Get the time of the last snapshot.
    """
    try:
        with open(globals.FS_SNAPSHOT_FILE, 'r') as f:
            return datetime.datetime.fromisoformat(f.readline().strip())
    except (FileNotFoundError, ValueError):
        return None

