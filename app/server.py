import json
import os
import queue
import shutil
import time
import uuid
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename
from urllib.parse import unquote, urlparse

from app.announcer import EventAnnouncer
from app.cloud_adapters import s3_adapter
import app.globals as globals
import app.slideshow as slideshow
import app.utils.aws as aws
import app.utils.filesystem as filesystem
import app.utils.offline as offline
import app.utils.utils as utils

utils.load_env([".env", globals.ENV_FILE])

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = globals.MAX_CONTENT_LENGTH
app.config['UPLOAD_EXTENSIONS'] = globals.ALLOWED_FILE_EXTENSIONS

cloud_adapter = s3_adapter.S3Adapter(os.getenv('S3_BUCKET_NAME', 'pi-photo-album-s3'))
event_announcer = EventAnnouncer()

def enforce_mime(mime_type):
    def decorator(func):
        def wrapper(*args, **kwargs):
            content_type = request.content_type
            if content_type.split(';')[0] != mime_type:
                return jsonify({"status": "error", "message": f"Invalid content type. Expected {mime_type}."}), 400
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

@app.route('/', methods=['GET'])
def index():
    settings = slideshow.load_settings()
    username = os.getenv('USERNAME')
    if not username:
        raise ValueError("Environment variable 'USERNAME' must be set.")
    default_file_structure = filesystem.get_default_file_structure(username)
    file_structure = filesystem.get_file_structure(f"{globals.BASE_DIR}/albums")

    # Ensure that the default file structure is always present at a minimum.
    file_structure = utils.partial_dict_merge(file_structure, default_file_structure)
    return render_template('index.html', settings=settings, fileStructure=file_structure)

@app.route('/save-settings', methods=['POST'])
@enforce_mime('application/json')
def save_settings():
    settings: dict | None = request.json
    if not settings:
        return jsonify({"status": "ok"})

    # Some settings validation
    if 'album' not in settings or type(settings["album"]) is not str:
        return jsonify({"status": "error", "message": "Invalid value for album"}), 400
    if 'isEnabled' not in settings or type(settings["isEnabled"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for isEnabled"}), 400
    if 'blend' not in settings or type(settings["blend"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for blend"}), 400
    if 'speed' not in settings or type(settings["speed"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for speed"}), 400
    if 'randomize' not in settings or type(settings["randomize"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for randomize"}), 400

    prev_settings = slideshow.load_settings()

    cleaned_settings = {
        "album": settings["album"],
        "isEnabled": settings["isEnabled"],
        "blend": utils.clamp(settings["blend"], 0, 1000),
        "speed": utils.clamp(settings["speed"], 0, 180),
        "randomize": settings["randomize"],
    }

    slideshow.save_settings_to_file(cleaned_settings)

    slideshow.stop_slideshow()
    album_path = f"{globals.BASE_DIR}/albums/{cleaned_settings['album']}"
    if (cleaned_settings["randomize"] != prev_settings["randomize"] 
        or cleaned_settings["album"] != prev_settings["album"]):
        # Must be set to recursive b/c inotifywait is setup to watch recursively.
        slideshow.set_image_order(album_path, cleaned_settings["randomize"], True)
    if cleaned_settings["isEnabled"]:
        time.sleep(1)
        slideshow.start_slideshow(album_path, cleaned_settings["blend"], cleaned_settings["speed"])

    return jsonify({"status": "ok"})

@app.route('/shuffle', methods=['POST'])
def shuffle():
    settings = slideshow.load_settings()
    if settings["album"]:
        album_path = f"{globals.BASE_DIR}/albums/{settings['album']}"
        # Must be set to recursive b/c inotifywait is setup to watch recursively.
        slideshow.set_image_order(album_path, True, True)
        if settings["isEnabled"]:
            slideshow.stop_slideshow()
            time.sleep(1)
            slideshow.start_slideshow(album_path, settings["blend"], settings["speed"])
    return jsonify({"status": "ok"})

@app.route('/upload-images', methods=['POST'])
@enforce_mime('multipart/form-data')
def upload_images():
    file_ids: dict[str, str] = {} # Dict[filename: guid]
    saved_files: list[tuple[str, str]] = [] # List[(guid, file_path)]
    heif_files: list[tuple[str, str]] = [] # List[(guid, file_path)]
    failed_files: list[str] = [] # List[guid]

    req_metadata = request.form.get("metadata")
    if not req_metadata:
        return jsonify({"status": "error", "message": "No metadata provided"}), 400
    try:
        file_ids = json.loads(req_metadata)["files"]
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid metadata provided"}), 400

    album_paths = request.files.keys()
    # Sanatize file paths
    album_paths = [utils.secure_path(album_path) for album_path in album_paths]   
    for album_path in album_paths:
        images = request.files.getlist(album_path)
        for image in images:
            if not image.filename:
                continue
            # guid comes from the request data. It's not a trusted value! It's only use is to identify the files that failed to upload to cloud.
            guid = file_ids.get(image.filename, "") 
            image_name = f'{uuid.uuid4()}.{secure_filename(image.filename)}'
            file_extension = utils.get_file_extension(image_name)
            if file_extension not in app.config['UPLOAD_EXTENSIONS'] or not filesystem.is_file_owner(album_path):
                failed_files.append(guid)
                continue

            if file_extension in {'heif', 'heic'}:
                heif_files.append((guid, image_name))
                image.save(f"{globals.TMP_STORAGE_DIR}/{image_name}") # Save to tmp storage
            else:
                loc = utils.save_image_to_disk(f'{globals.BASE_DIR}/albums/{album_path}', image_name, image, True)
                saved_files.append((guid, loc))

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [f"{globals.BASE_DIR}/albums/{os.path.dirname(heif_file[1])}/{heif_file[1].rsplit('.', 1)[0]}.jpg" for heif_file in heif_files]
        heif_paths = [f"{globals.TMP_STORAGE_DIR}/{heif_file[1]}" for heif_file in heif_files]
        exit_codes = utils.multiple_heif_to_jpg(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            saved_files.append((heif_files[i][0], jpg_paths[i])) if code == 0 else failed_files.append(heif_files[i][0])

    if not aws.ping(globals.S3_PING_URL):
        offline_events = [offline.create_offline_event('PUT', sf[1]) for sf in saved_files]
        offline.save_offline_events(globals.OFFLINE_EVENTS_FILE, offline_events)
    elif len(saved_files) > 0:
        # Bulk upload to cloud
        success, failure = cloud_adapter.insert_bulk([sf[1] for sf in saved_files], [filesystem.strip_base_dir(sf[1]) for sf in saved_files])
        failed_files = failed_files + [sf[0] for sf in saved_files if filesystem.strip_base_dir(sf[1]) in failure]

        # Push events to queue
        message = json.dumps({"events": [{"event": "PUT", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    # failed: the guids of the files that failed to upload.
    # success: the paths of the files that were successfully uploaded.
    # return jsonify({"status": "ok", "failed": failed_files, "success": success})
    return jsonify({"status": "ok", "failed": [], "success": [filesystem.strip_base_dir(sf[1]) for sf in saved_files]})

@app.route('/delete-images', methods=['POST'])
@enforce_mime('application/json')
def delete_images():
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})
    
    # for f in files:
    #     f = utils.secure_path(f)
    #     filesystem.silentremove(filesystem.key_to_abs_path(f))
    #     filesystem.remove_dirs(f'{globals.BASE_DIR}/albums', filesystem.remove_albums_prefix(os.path.dirname(f)))

    if not aws.ping(globals.S3_PING_URL):
        offline_events = [offline.create_offline_event('DELETE', sf) for sf in files]
        offline.save_offline_events(globals.OFFLINE_EVENTS_FILE, offline_events)
    elif len(files) > 0:
        print(files)
        success, failed = cloud_adapter.delete_bulk(files)
        print(success, failed)
        message = json.dumps({"events": [{"event": "DELETE", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    return jsonify({"status": "ok", "failed": []})

@app.route('/move-images', methods=['POST'])
@enforce_mime('application/json')
def move_images():
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    files_to_move = []
    for file in files:
        file['oldPath'] = utils.secure_path(file['oldPath'])
        file['newPath'] = utils.secure_path(file['newPath'])
        if not filesystem.is_file_owner(file['oldPath']) or not filesystem.is_file_owner(file['newPath']):
            print(f"File is not owned by the user. {file['oldPath']} -> {file['newPath']}")
            continue
        if filesystem.key_to_abs_path(file['oldPath']) == filesystem.key_to_abs_path(file['newPath']):
            continue

        new_path = filesystem.key_to_abs_path(file['newPath'])
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(filesystem.key_to_abs_path(file['oldPath']), new_path)
        filesystem.remove_dirs(f'{globals.BASE_DIR}/albums', filesystem.remove_albums_prefix(os.path.dirname(file['oldPath'])))
        files_to_move.append(file)

    if not aws.ping(globals.S3_PING_URL):
        offline_events = [offline.create_offline_event('MOVE', sf['oldPath'], sf['newPath']) for sf in files_to_move]
        offline.save_offline_events(globals.OFFLINE_EVENTS_FILE, offline_events)
    elif len(files_to_move) > 0:
        image_key_pairs = [(f['oldPath'], f['newPath']) for f in files_to_move]
        success, failed = cloud_adapter.move_bulk(image_key_pairs)
        message = json.dumps({"events": [{"event": "MOVE", "path": sf[0], "newPath": sf[1]} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    # failed: List[(old_path, new_path)]
    return jsonify({"status": "ok", "failed": []})

@app.route('/copy-images', methods=['POST'])
@enforce_mime('application/json')
def copy_images():
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    files_to_copy = []
    for file in files:
        file['oldPath'] = utils.secure_path(file['oldPath'])
        file['newPath'] = utils.secure_path(file['newPath'])
        if not filesystem.is_file_owner(file['oldPath']) or not filesystem.is_file_owner(file['newPath']):
            print(f"File is not owned by the user. {file['oldPath']} -> {file['newPath']}")
            continue
        if filesystem.key_to_abs_path(file['oldPath']) == filesystem.key_to_abs_path(file['newPath']):
            continue

        new_path = filesystem.key_to_abs_path(file['newPath'])
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        shutil.copyfile(filesystem.key_to_abs_path(file['oldPath']), new_path)
        files_to_copy.append(file)

    if not aws.ping(globals.S3_PING_URL):
        offline_events = [offline.create_offline_event('PUT', sf['newPath']) for sf in files_to_copy]
        offline.save_offline_events(globals.OFFLINE_EVENTS_FILE, offline_events)
    elif len(files_to_copy) > 0:
        image_keys = [f['newPath'] for f in files_to_copy]
        success, failure = cloud_adapter.insert_bulk([filesystem.key_to_abs_path(k) for k in image_keys], image_keys)
        message = json.dumps({"events": [{"event": "PUT", "path": s} for s in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    return jsonify({"status": "ok", "failed": []})

@app.route('/receive-events', methods=['POST'])
@enforce_mime('application/json')
def receive_events():
    payload: dict | None = request.json
    if not payload:
        return jsonify({"status": "ok"})

    processed_events = []

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
                        image = cloud_adapter.get(path)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, 'wb') as f:
                            f.write(image)
                case "DELETE":
                    print(f"EVENT: Deleting {event['path']}")
                    filesystem.silentremove(f"{globals.BASE_DIR}/{event['path']}")
                    filesystem.remove_dirs(f'{globals.BASE_DIR}/albums', filesystem.remove_albums_prefix(os.path.dirname(event['path'])))
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
                        image = cloud_adapter.get(new_path)
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
                    filesystem.remove_dirs(f'{globals.BASE_DIR}/albums', filesystem.remove_albums_prefix(os.path.dirname(old_path)))
            processed_events.append(event)
        except Exception as e:
            print(f"Error processing event: {e}")
            continue

    event_announcer.announce(json.dumps({"events": processed_events, "sender": os.getenv('USERNAME')}))
    return jsonify({"status": "ok"})

@app.route('/stream-events', methods=['GET'])
def stream_events():
    def generator():
        events_queue = event_announcer.subscribe()
        keep_alive_interval = 120
        while True:
            try:
                event = events_queue.get(timeout=keep_alive_interval)
                yield event
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(generator(), mimetype='text/event-stream')

@app.route('/resync', methods=['POST'])
def resync():
    """
    Resync the filesystem with the cloud storage.
    """
    event_announcer.announce(json.dumps({"events": [{"event": "LOADING", "loading": True, "message": "Resyncing photos with cloud storage..."}], "sender": os.getenv('USERNAME')}))

    prefixes = [f"albums/{prefix}" for prefix in globals.ALLOWED_PREFIXES]

    if not aws.ping(globals.S3_PING_URL):
        return jsonify({"status": "error", "message": "Offline"}), 500

    cloud_files = set()
    for prefix in prefixes:
        # trailing slash required b/c of s3 policy
        cloud_files.update(cloud_adapter.list_album(f'{prefix}/'))

    local_files = set(filesystem.list_files_in_dir(globals.BASE_DIR, prefixes))

    files_not_in_cloud = local_files.difference(cloud_files)
    files_not_in_local = cloud_files.difference(local_files)

    offline_events = offline.get_offline_events(globals.OFFLINE_EVENTS_FILE)
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
    cloud_adapter.get_bulk([filesystem.key_to_abs_path(f) for f in files_not_in_local], list(files_not_in_local))
    
    print("Deleting from local:")
    print(files_not_in_cloud)
    for path in files_not_in_cloud:
        filesystem.silentremove(filesystem.key_to_abs_path(path))

    cloud_adapter.insert_queue(json.dumps({"events": events_to_send, "sender": os.getenv('USERNAME')}))
    
    event_announcer.announce(json.dumps(
        {
            "events": [
                {"event": "RESYNC", "fileStructure": filesystem.get_file_structure(f"{globals.BASE_DIR}/albums")},
                {"event": "LOADING", "loading": False}
            ], 
            "sender": os.getenv('USERNAME')
        }
    ))

    print("Clearing offline events")
    offline.clear_offline_events(globals.OFFLINE_EVENTS_FILE)

    return jsonify({"status": "ok"})

@app.route('/preview', methods=['GET'])
def preview():
    image_path = request.args.get('image')
    if not image_path:
        return jsonify({"status": "error", "message": "Invalid image path"}), 400
    
    image_path = unquote(image_path)

    # Reject non-local paths.
    if urlparse(image_path).scheme != '' or urlparse(image_path).netloc != '':
        return jsonify({"status": "error", "message": "Invalid image path"}), 400

    if not os.path.exists(filesystem.key_to_abs_path(image_path)):
        return jsonify({"status": "error", "message": "Image not found"}), 404

    return send_from_directory(globals.BASE_DIR, image_path)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    os.makedirs(globals.CONFIG_DIR, exist_ok=True)
    os.makedirs(f"{globals.BASE_DIR}/albums", exist_ok=True)
    os.makedirs(globals.TMP_STORAGE_DIR, exist_ok=True)

    # Starts slideshow on startup if it's enabled in the settings.
    settings = slideshow.load_settings()
    if settings["isEnabled"]:
        album_path = f"{globals.BASE_DIR}/albums/{settings['album']}"
        slideshow.start_slideshow(album_path, settings["blend"], settings["speed"])

    app.run(debug=True, host='0.0.0.0', use_reloader=False, port=int(os.getenv('API_PORT', 5555)))