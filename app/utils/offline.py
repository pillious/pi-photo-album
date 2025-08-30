"""
Utilities for handling when the app goes offline.
"""

import os
import json
import csv
from datetime import datetime, timezone, timedelta

from app.config.config import config
from app.utils import offline, filesystem

def write_poll_time():
    """
    Write the current timestamp to the last_poll file.
    Resilient to crashes and restarts.
    """
    last_poll_file = config()['paths']['last_poll_file'].as_str()
    timestamp = str(datetime.now(timezone.utc))
    tmp_file = f'{last_poll_file}.tmp'
    with open(tmp_file, 'w') as f:
        f.write(timestamp + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_file, last_poll_file)

def get_last_poll():
    """
    Read the last poll timestamp from file.
    If the file does not exist or is empty, returns 1 January 1970.
    """
    try:
        last_poll_file = config()['paths']['last_poll_file'].as_str()
        print(last_poll_file)
        with open(last_poll_file, 'r') as f:
            return datetime.fromisoformat(f.readline().strip())
    except (FileNotFoundError, ValueError):
        return datetime.fromtimestamp(0, timezone.utc)

def is_within_retention_period():
    """
    Check if the last poll time is within the queue retention period.
    """
    queue_retention_days = config()['queue']['retention_days'].as_int()
    last_poll_time = get_last_poll()
    lower_bound = datetime.now(timezone.utc) - timedelta(days=queue_retention_days)
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
    allowed_prefixes = config()['files']['allowed_prefixes'].as_set().as_strs()
    base_dir = config()['paths']['base_dir'].as_str()
    prefixes = [f"albums/{prefix}" for prefix in allowed_prefixes]
    file_paths = filesystem.list_files_in_dir(base_dir, prefixes)

    with open(out_file, 'w') as f:
        f.write(str(offline.get_last_poll()))
        f.write("\n")
        f.write(json.dumps(file_paths))

def create_offline_event(event: str, path: str, new_path = ''):
    """
    Create an offline event in the format:
    ```
    <timestamp>,<event>,<path>[,<new_path>]
    ```
    """
    timestamp = str(datetime.now(timezone.utc))
    if event == 'MOVE':
        return f"{timestamp},{event},{path},{new_path}"
    return f"{timestamp},{event},{path}"

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
        fs_snapshot_file = config()['paths']['fs_snapshot_file'].as_str()
        with open(fs_snapshot_file, 'r') as f:
            return datetime.fromisoformat(f.readline().strip())
    except (FileNotFoundError, ValueError):
        return None

