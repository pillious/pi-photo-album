import json
from typing import Dict, List, Tuple
from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
import os
import queue

from announcer import EventAnnouncer
from cloud_adapters import s3_adapter
import slideshow
import utils
import globals

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = globals.MAX_CONTENT_LENGTH
app.config['UPLOAD_EXTENSIONS'] = globals.ALLOWED_FILE_EXTENSIONS

cloud_adapter = s3_adapter.S3Adapter('pi-photo-album-s3')
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
    default_file_structure = utils.get_default_file_structure(os.getenv('USERNAME'))
    file_structure = utils.get_file_structure(f"{globals.BASE_DIR}/albums")
    file_structure = utils.partial_dict_merge(file_structure, default_file_structure)
    return render_template('index.html', settings=settings, fileStructure=file_structure)

@app.route('/save-settings', methods=['POST'])
@enforce_mime('application/json')
def save_settings():
    settings = request.json

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

    cleanedSettings = {
        "album": settings["album"],
        "isEnabled": settings["isEnabled"],
        "blend": utils.clamp(settings["blend"], 0, 1000),
        "speed": utils.clamp(settings["speed"], 0, 180),
        "randomize": settings["randomize"]
    }

    print(cleanedSettings)
    slideshow.save_settings_to_file(cleanedSettings)

    # Update display with the new settings.
    print(slideshow.stop_slideshow())
    if cleanedSettings["isEnabled"]:
        album_path = f"{globals.BASE_DIR}/albums/{cleanedSettings['album']}"
        print(slideshow.start_slideshow(album_path, cleanedSettings["blend"], cleanedSettings["speed"], cleanedSettings["randomize"]))

    return jsonify({"status": "ok"})

@app.route('/upload-images', methods=['POST'])
@enforce_mime('multipart/form-data')
def upload_images():
    file_ids: Dict[Tuple[str, str]] = {} # Dict[filename: guid]
    saved_files: List[Tuple[str, str]] = [] # List[(guid, file_path)]
    heif_files: List[Tuple[str, str]] = [] # List[(guid, file_path)]
    failed_files: List[str] = [] # List[guid]

    req_metadata = request.form.get("metadata")
    if not req_metadata:
        return jsonify({"status": "error", "message": "No metadata provided"}), 400
    try:
        file_ids = json.loads(req_metadata)["files"]
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid metadata provided"}), 400

    IS_ONLINE = True

    album_paths = request.files.keys()
    # Sanatize file paths
    album_paths = ["/".join([secure_filename(p) for p in album_path.split('/')]) for album_path in album_paths]   
    for album_path in album_paths:
        images = request.files.getlist(album_path)
        for image in images:
            # guid comes from the request data. It's not a trusted value! It's only use is to identify the files that failed to upload to cloud.
            guid = file_ids.get(image.filename, "") 
            image_name = f'{uuid.uuid4()}.{secure_filename(image.filename)}'
            file_extension = utils.get_file_extension(image_name)
            if file_extension not in app.config['UPLOAD_EXTENSIONS'] or album_path.split('/')[0] not in globals.ALLOWED_PREFIXES:
                failed_files.append(guid)
                continue

            if file_extension in {'heif', 'heic'}:
                heif_files.append((guid, image_name))
                image.save(f"{globals.TMP_STORAGE}/{image_name}") # Save to tmp storage
                print(f"{globals.TMP_STORAGE}/{image_name}")
            else:
                loc = utils.save_image_to_disk(f'{globals.BASE_DIR}/albums/{album_path}', image_name, image, True)
                saved_files.append((guid, loc))

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [f"{globals.BASE_DIR}/albums/{album_path}/{heif_file[1].rsplit('.', 1)[0]}.jpg" for heif_file in heif_files]
        heif_paths = [f"{globals.TMP_STORAGE}/{heif_file[1]}" for heif_file in heif_files]
        exit_codes = utils.multiple_heif_to_jpg(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            saved_files.append((heif_files[i][0], jpg_paths[i])) if code == 0 else failed_files.append(heif_files[i][0])

    if IS_ONLINE and len(saved_files) > 0:     
        # Bulk upload to cloud
        success, failure = cloud_adapter.insertBulk([sf[1] for sf in saved_files], [sf[1][len(f"{globals.BASE_DIR}/"):] for sf in saved_files])
        failed_files = failed_files + [sf[0] for sf in saved_files if sf[1][len(f"{globals.BASE_DIR}/"):] in failure]
        print(success,failure, failed_files)
        # Push events to queue
        # for sf in success:
        #     message = json.dumps({"event": "PUT", "path": sf, "sender": os.getenv('USERNAME')})
        #     cloud_adapter.insertQueue(message)
    else:
        success = [sf[1][len(f"{globals.BASE_DIR}/"):] for sf in saved_files]

    # failed: the guids of the files that failed to upload.
    # success: the paths of the files that were successfully uploaded.
    return jsonify({"status": "ok", "failed": failed_files, "success": success})

@app.route('/receive-events', methods=['POST'])
@enforce_mime('application/json')
def receive_events():
    payload = request.json

    # {'events': ['{"event": "PUT", "path": "albums/Shared/0eb9fc9e-757b-4c6e-95d5-d7cda4b8e802.webcam-settings.png", "timestamp": 1745101204, "id": "142b9797-a2fe-48ed-8ec1-f875b5fb82d9"}']}
    # "newPath"
    # expected to be in order

    print(payload)

    for e in payload['events']:
        event = json.loads(e)
        match event["event"]:
            case "PUT":
                image = cloud_adapter.get(event["path"])
                image_path = f'{globals.BASE_DIR}/{event["path"]}'
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                with open(image_path, 'wb') as f:
                    f.write(image)
            case "DELETE":
                continue
            case "MOVE":
                continue

    event_announcer.announce(json.dumps(payload))
            
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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    os.makedirs(f"{globals.BASE_DIR}/albums", exist_ok=True)
    os.makedirs(globals.TMP_STORAGE, exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=os.getenv('API_PORT', 5000))