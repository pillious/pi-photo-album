import json
from typing import Dict, List, Tuple
from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
import os
import queue

from app.announcer import EventAnnouncer
from app.cloud_adapters import s3_adapter
import app.slideshow as slideshow
import app.utils.utils as utils
import app.utils.filesystem as filesystem
import app.globals as globals

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
    default_file_structure = filesystem.get_default_file_structure(os.getenv('USERNAME'))
    file_structure = filesystem.get_file_structure(f"{globals.BASE_DIR}/albums")

    # Ensure that the default file structure is always present.
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
            if file_extension not in app.config['UPLOAD_EXTENSIONS'] or not utils.is_file_owner(album_path):
                failed_files.append(guid)
                continue

            if file_extension in {'heif', 'heic'}:
                heif_files.append((guid, image_name))
                image.save(f"{globals.TMP_STORAGE_DIR}/{image_name}") # Save to tmp storage
                print(f"{globals.TMP_STORAGE_DIR}/{image_name}")
            else:
                loc = utils.save_image_to_disk(f'{globals.BASE_DIR}/albums/{album_path}', image_name, image, True)
                saved_files.append((guid, loc))

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [f"{globals.BASE_DIR}/albums/{album_path}/{heif_file[1].rsplit('.', 1)[0]}.jpg" for heif_file in heif_files]
        heif_paths = [f"{globals.TMP_STORAGE_DIR}/{heif_file[1]}" for heif_file in heif_files]
        exit_codes = utils.multiple_heif_to_jpg(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            saved_files.append((heif_files[i][0], jpg_paths[i])) if code == 0 else failed_files.append(heif_files[i][0])

    if IS_ONLINE and len(saved_files) > 0:     
        # Bulk upload to cloud
        success, failure = cloud_adapter.insert_bulk([sf[1] for sf in saved_files], [sf[1][len(f"{globals.BASE_DIR}/"):] for sf in saved_files])
        failed_files = failed_files + [sf[0] for sf in saved_files if sf[1][len(f"{globals.BASE_DIR}/"):] in failure]
        print(success,failure, failed_files)

        # Push events to queue
        message = json.dumps({"events": [{"event": "PUT", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    else:
        success = [sf[1][len(f"{globals.BASE_DIR}/"):] for sf in saved_files]

    # failed: the guids of the files that failed to upload.
    # success: the paths of the files that were successfully uploaded.
    return jsonify({"status": "ok", "failed": failed_files, "success": success})

@app.route('/delete-images', methods=['POST'])
@enforce_mime('application/json')
def delete_images():
    files = request.json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})
    
    for f in files:
        os.remove(f"{globals.BASE_DIR}/{f}")

    success, failed = cloud_adapter.delete_bulk(files)
    print(success, failed)

    if success:
        message = json.dumps({"events": [{"event": "DELETE", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    return jsonify({"status": "ok", "failed": failed})

@app.route('/move-images', methods=['POST'])
@enforce_mime('application/json')
def move_images():
    files = request.json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    # TODO: sanatize the paths & file name

    for file in files:
        if not filesystem.is_file_owner(file['oldPath']) or not filesystem.is_file_owner(file['newPath']):
            print(f"File is not owned by the user. {file['oldPath']} -> {file['newPath']}")
            continue

        print(f"{globals.BASE_DIR}/{file['oldPath']}", f"{globals.BASE_DIR}/{file['newPath']}")
        print("-------------")
        new_path = f"{globals.BASE_DIR}/{file['newPath']}"
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(f"{globals.BASE_DIR}/{file['oldPath']}", new_path)

    image_key_pairs = [(f['oldPath'], f['newPath']) for f in files]
    success, failed = cloud_adapter.move_bulk(image_key_pairs)
    print(success, failed)

    if success:
        message = json.dumps({"events": [{"event": "MOVE", "path": sf[0], "newPath": sf[1]} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_adapter.insert_queue(message)

    # failed: List[(old_path, new_path)]
    return jsonify({"status": "ok", "failed": []})

@app.route('/receive-events', methods=['POST'])
@enforce_mime('application/json')
def receive_events():
    payload = request.json
    processed_events = []
    print(payload)

    # {'events': [{"event": "PUT", "path": "albums/Shared/0eb9fc9e-757b-4c6e-95d5-d7cda4b8e802.webcam-settings.png", "timestamp": 1745101204, "id": "142b9797-a2fe-48ed-8ec1-f875b5fb82d9"}]}
    # "newPath"
    # expected to be in order

    for event in payload['events']:
        try: 
            match event["event"]:
                case "PUT":
                    print(f"EVENT: Creating {event['path']}")
                    path, abs_path = event["path"], f"{globals.BASE_DIR}/{event['path']}"
                    if filesystem.is_file_owner(path):
                        image = cloud_adapter.get(path)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, 'wb') as f:
                            f.write(image)
                case "DELETE":
                    print(f"EVENT: Deleting {event['path']}")
                    os.remove(f"{globals.BASE_DIR}/{event['path']}")
                case "MOVE":
                    old_path, abs_old_path = event['path'], f"{globals.BASE_DIR}/{event['path']}"
                    new_path, abs_new_path = event['newPath'], f"{globals.BASE_DIR}/{event['newPath']}"
                    print(f"EVENT: Moving {event['path']} to {event['newPath']}")
                    if filesystem.is_file_owner(old_path) and filesystem.is_file_owner(new_path):
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
                        os.remove(abs_old_path)
                        event["event"] = "DELETE"
                        event["path"] = old_path
                        del event["newPath"]
                # TODO: handle empty folders after move.
                # can probably be some utility function that takes a path and goes up the path chain.
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
    prefixes = [f"albums/{prefix}/" for prefix in globals.ALLOWED_PREFIXES]

    # cloud_files = set()
    # for prefix in prefixes:
        # cloud_files.update(cloud_adapter.list_album(prefix))

    local_files = set(filesystem.list_files_in_dir(globals.BASE_DIR, prefixes))

    # TEMP: for testing
    l1 = ['albums/Shared/0eb9fc9e-757b-4c6e-95d5-d7cda4b8e802.webcam-settings.png', 'albums/Shared/123.png', 'albums/Shared/19dfbc98-2a82-43da-802b-8ad5a5b5f32a.webcam-settings.png', 'albums/Shared/2e290df-75e3-49ce-ba0a-4273337e4274.123.png', 'albums/Shared/2eeda593-fb98-4a6b-9a52-41ca44faceb6.webcam-settings.png', 'albums/Shared/4a0983d0-ce2a-4009-a74c-641545d8d14b.webcam-settings.png', 'albums/Shared/615fdba2-72e0-4ffe-8793-83495bc2f159.testimage_-_Copy.png', 'albums/Shared/be9b074b-814e-4aaa-855b-87dce0dd9d1f.webcam-settings.png', 'albums/Shared/c585ecab-59db-450f-abb8-3d76f97bf172.webcam-settings.png', 'albums/Shared/dae13468-65fd-442a-83b9-35ab1194b4c4.webcam-settings.png', 'albums/Shared/ef4b2f52-b960-48d6-8a86-fcb4ac529c7f.testimage_-_Copy.png', 'albums/Shared/test2/11a1d5b2-fa89-4c9a-9ae9-50bf1299ca0e.webcam-settings.png', 'albums/Shared/test2/29c2f73a-0a5f-4d04-a67c-a00440e3b951.randomphoto.png', 'albums/Shared/test2/9ff70ffd-445f-4642-aa7f-3d39e80b0dd5.webcam-settings.png', 'albums/Shared/testing/asdf/09faab5c-9fe5-493a-ba18-e11d58453cd1.testimage_-_Copy.png', 'albums/Shared/testing/asdf/604c9748-3a89-49bd-9be5-3d00d8f3b36c.webcam-settings.png', 'albums/Shared/user1test/288fb391-ea2b-4f3b-90bd-fb400a326309.webcam-settings.png', 'albums/Shared/user1test/3300954b-469e-4c86-84eb-642ce9944f22.randomphoto.png', 'albums/Shared/user1test/3ff97bd5-94e0-4ce6-8cc7-d03bdeac677c.randomphoto.png', 'albums/Shared/user1test/514e05d5-59e4-4163-879c-9895d90089f1.randomphoto.png', 'albums/Shared/user1test/8c5cabbb-3408-4683-8468-99fa92b9a157.randomphoto.png', 'albums/Shared/user1test/b9f0f763-0b59-48d2-bfca-32974415ec76.webcam-settings.png', 'albums/Shared/user1test/bda535ba-3064-42f8-b21d-9e9f6ed17554.testimage_-_Copy.png', 'albums/Shared/user1test/f82db8b0-f7ed-49c6-b0c9-9315a2c1355f.webcam-settings.png', 'albums/Shared/user1test/subfolder1/09dad2ed-adb1-4421-9695-769a2be8a1e9.randomphoto.png', 'albums/Shared/user1test/subfolder1/6eb679c7-9fed-4592-8230-711f5c6e65e5.webcam-settings.png', 'albums/Shared/user1test/subfolder1/6f18a05a-bb79-4856-93f1-2b2ffe035a6c.randomphoto.png', 'albums/Shared/user1test/subfolder1/91040ce0-7cab-4979-8c43-2f81ebb7852e.testimage_-_Copy.png', 'albums/Shared/user1test/subfolder1/ca7e30be-255b-4cb1-9084-e6d0b3c119a5.webcam-settings.png', 'albums/Shared/user1test/test2/4b48e91e-9aba-4cd4-9bbc-98e6cafdf171.webcam-settings.png']
    l2 = ['albums/alee1246/nature/2a2d4c48-d6f5-4b46-869e-648dcf328c3d.testimage_-_Copy.png', 'albums/alee1246/nature/817ec81c-2b93-4fa6-aabf-2a31fa09226a.webcam-settings.png', 'albums/alee1246/nature/955cc36d-910b-49c2-b182-8aa41f335576.webcam-settings.png', 'albums/alee1246/user1test/subfolder1/04747157-9314-4c8d-8f39-41e172e97629.randomphoto.png', 'albums/alee1246/user1test/subfolder1/6808bb8a-6336-4912-9cd6-62db8f6d029a.webcam-settings.png']
    cloud_files = set(l1).union(set(l2))

    files_not_in_cloud = local_files.difference(cloud_files)
    files_not_in_local = cloud_files.difference(local_files)

    print(files_not_in_cloud)
    print(files_not_in_local)

    cloud_adapter.get_bulk([f"{globals.BASE_DIR}/{f}" for f in files_not_in_cloud], list(files_not_in_local))
    # TODO: handle case where the file has been deleted from the cloud but not from local.
    # Need to have a list of events that happened while offline so that we don't reupload the delete file.
    # cloud_adapter.insert_bulk([f"{globals.BASE_DIR}/{f}" for f in files_not_in_local], list(files_not_in_local))

    return jsonify({"status": "ok"})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    os.makedirs(globals.CONFIG_DIR, exist_ok=True)
    os.makedirs(f"{globals.BASE_DIR}/albums", exist_ok=True)
    os.makedirs(globals.TMP_STORAGE_DIR, exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=os.getenv('API_PORT', 5000))