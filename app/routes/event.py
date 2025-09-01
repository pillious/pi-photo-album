from flask import Request, jsonify, Response
import os
import json
import queue

from app.utils import filesystem, offline, aws
from app.announcer import event_announcer
from app.cloud_clients.cloud_client import cloud_client
from app.config.config import config

def receive_events(request: Request):
    payload: dict | None = request.json
    if not payload:
        return jsonify({"status": "ok"})


    processed_events = []
    base_dir = config()['paths']['base_dir'].as_str()

    # {'events': [{"event": "PUT", "path": "albums/Shared/0eb9fc9e-757b-4c6e-95d5-d7cda4b8e802.webcam-settings.png", "timestamp": 1745101204, "id": "142b9797-a2fe-48ed-8ec1-f875b5fb82d9"}]}
    # "newPath"
    # expected to be in order

    for event in payload['events']:
        try:
            match event["event"]:
                case "PUT":
                    print(f"EVENT: Creating {event['path']}")
                    path, abs_path = event["path"], filesystem.key_to_abs_path(event['path'])
                    if filesystem.is_file_owner(path):
                        image = cloud_client().get(path)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, 'wb') as f:
                            f.write(image)
                case "DELETE":
                    print(f"EVENT: Deleting {event['path']}")
                    filesystem.silentremove(f"{base_dir}/{event['path']}")
                    filesystem.remove_dirs(f'{base_dir}/albums', filesystem.remove_albums_prefix(os.path.dirname(event['path'])))
                case "MOVE":
                    old_path, abs_old_path = event['path'], filesystem.key_to_abs_path(event['path'])
                    new_path, abs_new_path = event['newPath'], filesystem.key_to_abs_path(event['newPath'])
                    print(f"EVENT: Moving {event['path']} to {event['newPath']}")
                    if filesystem.is_file_owner(old_path) and filesystem.is_file_owner(new_path):
                        if os.path.exists(abs_new_path):
                            filesystem.silentremove(abs_old_path)
                        else:
                            os.makedirs(os.path.dirname(abs_new_path), exist_ok=True)
                            os.rename(abs_old_path, abs_new_path)
                    elif not filesystem.is_file_owner(old_path):
                        # file is moved from a private folder, download it from the cloud
                        image = cloud_client().get(new_path)
                        os.makedirs(os.path.dirname(abs_new_path), exist_ok=True)
                        with open(abs_new_path, 'wb') as f:
                            f.write(image)
                        event["event"] = "PUT"
                        event["path"] = new_path
                        del event["newPath"]
                    elif not filesystem.is_file_owner(new_path):
                        # file is moved to a private folder, delete the old file.
                        filesystem.silentremove(abs_old_path)
                        event["event"] = "DELETE"
                        event["path"] = old_path
                        del event["newPath"]
                    filesystem.remove_dirs(f'{base_dir}/albums', filesystem.remove_albums_prefix(os.path.dirname(old_path)))
            processed_events.append(event)
        except Exception as e:
            print(f"Error processing event: {e}")
            continue

    event_announcer().announce(json.dumps({"events": processed_events, "sender": os.getenv('USERNAME')}))
    return jsonify({"status": "ok"})

def resync():
    """
    Resync the filesystem with the cloud storage.
    """
    event_announcer().announce(json.dumps({"events": [{"event": "LOADING", "loading": True, "message": "Resyncing photos with cloud storage..."}], "sender": os.getenv('USERNAME')}))

    allowed_prefixes = config()['files']['allowed_prefixes'].as_set().as_strs()
    s3_ping_url = config()['url']['s3_ping_url'].as_str()
    base_dir = config()['paths']['base_dir'].as_str()
    offline_events_file = config()['paths']['offline_events_file'].as_str()

    prefixes = [f"albums/{prefix}" for prefix in allowed_prefixes]


    if not aws.ping(s3_ping_url):
        return jsonify({"status": "error", "message": "Offline"}), 500

    cloud_files = set()
    for prefix in prefixes:
        # trailing slash required b/c of s3 policy
        cloud_files.update(cloud_client().list_album(f'{prefix}/'))

    local_files = set(filesystem.list_files_in_dir(base_dir, prefixes))

    files_not_in_cloud = local_files.difference(cloud_files)
    files_not_in_local = cloud_files.difference(local_files)

    offline_events = offline.get_offline_events(offline_events_file)
    for evt in offline_events:
        evt["path"] = filesystem.strip_base_dir(evt["path"])
        if evt["event"] == "MOVE":
            evt["newPath"] = filesystem.strip_base_dir(evt["newPath"])
    print("Offline events:")
    print(offline_events)

    events_to_send = []
    for evt in offline_events:
        match evt["event"]:
            case "PUT":
                files_not_in_cloud.discard(evt["path"]) # Avoids deleting the file later.
                events_to_send.append({"event": "PUT", "path": evt["path"]})
            case "MOVE":
                # TODO: test multiple moves of the same file while offline.
                files_not_in_local.discard(evt["path"]) # Avoids downloading the file later.
                files_not_in_cloud.discard(evt["newPath"]) # Avoids deleting the file later.
                events_to_send.append({"event": "MOVE", "path": evt["path"], "newPath": evt["newPath"]})
            case "DELETE":
                files_not_in_local.discard(evt["path"]) # Avoids downloading the file later.
                events_to_send.append({"event": "DELETE", "path": evt["path"]})

    print("Downloading from cloud:")
    print(files_not_in_local)
    cloud_client().get_bulk([filesystem.key_to_abs_path(f) for f in files_not_in_local], list(files_not_in_local))

    print("Deleting from local:")
    print(files_not_in_cloud)
    for path in files_not_in_cloud:
        filesystem.silentremove(filesystem.key_to_abs_path(path))

    cloud_client().insert_queue(json.dumps({"events": events_to_send, "sender": os.getenv('USERNAME')}))

    event_announcer().announce(json.dumps(
        {
            "events": [
                {"event": "RESYNC", "fileStructure": filesystem.get_file_structure(f"{base_dir}/albums")},
                {"event": "LOADING", "loading": False}
            ],
            "sender": os.getenv('USERNAME')
        }
    ))

    print("Clearing offline events")
    offline.clear_offline_events(offline_events_file)

    return jsonify({"status": "ok"})

def stream_events():
    def generator():
        events_queue = event_announcer().subscribe()
        keep_alive_interval = 120
        while True:
            try:
                event = events_queue.get(timeout=keep_alive_interval)
                yield event
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(generator(), mimetype='text/event-stream')
