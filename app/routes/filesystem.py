from flask import Request, jsonify, send_from_directory
import os
import json
import shutil
import uuid
from urllib.parse import unquote, urlparse
from werkzeug.utils import secure_filename

from app.config.config import config
from app.utils import utils, offline, filesystem, aws
from app.cloud_clients.cloud_client import cloud_client


class SavedFile:
    """Represents a file that has been saved to disk."""
    def __init__(self, guid: str, file_path: str):
        self.guid = guid
        self.file_path = file_path

    def get_file_path(self) -> str:
        """Get the full file path."""
        return self.file_path

    def get_guid(self) -> str:
        """Get the file GUID."""
        return self.guid

    def get_stripped_path(self) -> str:
        """Get the file path with base directory stripped."""
        return filesystem.strip_base_dir(self.file_path)

    def is_jpg(self) -> bool:
        """Check if the file is a JPG/JPEG."""
        return utils.get_file_extension(self.file_path) in {'jpg', 'jpeg'}


class HeifFile:
    """Represents a HEIF/HEIC file that needs to be converted to JPG."""
    def __init__(self, guid: str, album_path: str, image_name: str):
        self.guid = guid
        self.album_path = album_path
        # Format: <name>.<ext>
        self.image_name = image_name

    def get_guid(self) -> str:
        """Get the file GUID."""
        return self.guid

    def get_heif_path(self, tmp_storage_dir: str) -> str:
        """Get the full path to the temporary HEIF file."""
        return f"{tmp_storage_dir}/{self.image_name}"

    def get_jpg_path(self, base_dir: str) -> str:
        """Get the full path where the converted JPG should be saved."""
        jpg_name = self.image_name.rsplit('.', 1)[0] + '.jpg'
        return f"{base_dir}/albums/{self.album_path}/{jpg_name}"

def upload_images(request: Request):
    saved_files: list[SavedFile] = []
    heif_files: list[HeifFile] = []
    failed_files: list[str] = [] # List[guid]
    file_ids: dict[str, str] = {} # Dict[filename: guid]

    req_metadata = request.form.get("metadata")
    if not req_metadata:
        return jsonify({"status": "error", "message": "No metadata provided"}), 400
    try:
        file_ids = json.loads(req_metadata)["files"]
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid metadata provided"}), 400

    base_dir = config()['paths']['base_dir'].as_str()
    tmp_storage_dir = config()['paths']['tmp_storage_dir'].as_str()
    allowed_file_extensions = config()['files']['allowed_file_extensions'].as_set().as_strs()

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
            if file_extension not in allowed_file_extensions or not filesystem.is_file_owner(album_path):
                failed_files.append(guid)
                continue

            if file_extension in {'heif', 'heic'}:
                heif_files.append(HeifFile(guid, album_path, image_name))
                image.save(f"{tmp_storage_dir}/{image_name}")
            else:
                loc = utils.save_image_to_disk(f'{base_dir}/albums/{album_path}', image_name, image, True)
                saved_files.append(SavedFile(guid, loc))

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [heif_file.get_jpg_path(base_dir) for heif_file in heif_files]
        heif_paths = [heif_file.get_heif_path(tmp_storage_dir) for heif_file in heif_files]
        exit_codes = utils.heifs_to_jpgs(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            if code == 0:
                saved_files.append(SavedFile(heif_files[i].get_guid(), jpg_paths[i]))
            else:
                failed_files.append(heif_files[i].get_guid())

    # Parallelize the rotation of JPG files.
    jpg_paths = [sf.get_file_path() for sf in saved_files if sf.is_jpg()]
    if len(jpg_paths) > 0:
        utils.rotate_jpgs(jpg_paths)

    if not aws.ping(config()['url']['s3_ping_url'].as_str()):
        offline_events = [offline.create_offline_event('PUT', sf.get_file_path()) for sf in saved_files]
        offline_events_file = config()['paths']['offline_events_file'].as_str()
        offline.save_offline_events(offline_events_file, offline_events)
    elif len(saved_files) > 0:
        # Bulk upload to cloud
        success, failure = cloud_client().insert_bulk(
            [sf.get_file_path() for sf in saved_files],
            [sf.get_stripped_path() for sf in saved_files]
        )
        failed_files = failed_files + [sf.get_guid() for sf in saved_files if sf.get_stripped_path() in failure]

        # Push events to queue
        message = json.dumps({"events": [{"event": "PUT", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_client().insert_queue(message)

    # failed: the guids of the files that failed to upload.
    # success: the paths of the files that were successfully uploaded.
    # return jsonify({"status": "ok", "failed": failed_files, "success": success})
    if failed_files:
        print(f'failed to upload: {failed_files}')
    return jsonify({"status": "ok", "failed": [], "success": [sf.get_stripped_path() for sf in saved_files]})

def delete_images(request: Request):
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    base_dir = config()['paths']['base_dir'].as_str()
    s3_ping_url = config()['url']['s3_ping_url'].as_str()
    offline_events_file = config()['paths']['offline_events_file'].as_str()

    for f in files:
        f = utils.secure_path(f)
        filesystem.silentremove(filesystem.key_to_abs_path(f))
        filesystem.remove_dirs(f'{base_dir}/albums', filesystem.remove_albums_prefix(os.path.dirname(f)))

    if not aws.ping(s3_ping_url):
        offline_events = [offline.create_offline_event('DELETE', sf) for sf in files]
        offline.save_offline_events(offline_events_file, offline_events)
    elif len(files) > 0:
        print(files)
        success, failed = cloud_client().delete_bulk(files)
        print(success, failed)
        message = json.dumps({"events": [{"event": "DELETE", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_client().insert_queue(message)

    return jsonify({"status": "ok", "failed": []})

def move_images(request: Request):
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    base_dir = config()['paths']['base_dir'].as_str()
    s3_ping_url = config()['url']['s3_ping_url'].as_str()
    offline_events_file = config()['paths']['offline_events_file'].as_str()

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
        filesystem.remove_dirs(f'{base_dir}/albums', filesystem.remove_albums_prefix(os.path.dirname(file['oldPath'])))
        files_to_move.append(file)

    if not aws.ping(s3_ping_url):
        offline_events = [offline.create_offline_event('MOVE', sf['oldPath'], sf['newPath']) for sf in files_to_move]
        offline.save_offline_events(offline_events_file, offline_events)
    elif len(files_to_move) > 0:
        image_key_pairs = [(f['oldPath'], f['newPath']) for f in files_to_move]
        success, failed = cloud_client().move_bulk(image_key_pairs)
        message = json.dumps({"events": [{"event": "MOVE", "path": sf[0], "newPath": sf[1]} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_client().insert_queue(message)

    # failed: List[(old_path, new_path)]
    return jsonify({"status": "ok", "failed": []})

def copy_images(request: Request):
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "ok", "failed": []})
    files = req_json.get('files', [])
    if not files:
        return jsonify({"status": "ok", "failed": []})

    s3_ping_url = config()['url']['s3_ping_url'].as_str()
    offline_events_file = config()['paths']['offline_events_file'].as_str()

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

    if not aws.ping(s3_ping_url):
        offline_events = [offline.create_offline_event('PUT', sf['newPath']) for sf in files_to_copy]
        offline.save_offline_events(offline_events_file, offline_events)
    elif len(files_to_copy) > 0:
        image_keys = [f['newPath'] for f in files_to_copy]
        success, failure = cloud_client().insert_bulk([filesystem.key_to_abs_path(k) for k in image_keys], image_keys)
        message = json.dumps({"events": [{"event": "PUT", "path": s} for s in success], "sender": os.getenv('USERNAME')})
        cloud_client().insert_queue(message)

    return jsonify({"status": "ok", "failed": []})

def preview(request: Request):
    image_path = request.args.get('image')
    if not image_path:
        return jsonify({"status": "error", "message": "Invalid image path"}), 400

    image_path = unquote(image_path)

    # Reject non-local paths.
    if urlparse(image_path).scheme != '' or urlparse(image_path).netloc != '':
        return jsonify({"status": "error", "message": "Invalid image path"}), 400

    if not os.path.exists(filesystem.key_to_abs_path(image_path)):
        return jsonify({"status": "error", "message": "Image not found"}), 404

    base_dir = config()['paths']['base_dir'].as_str()
    return send_from_directory(base_dir, image_path)

def rotate_image(request: Request):
    req_json: dict | None = request.json
    if not req_json:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    image_path = req_json.get('path')
    rotation = req_json.get('rotation')
    if not image_path:
        return jsonify({"status": "error", "message": "No image path provided"}), 400
    if rotation is None:
        return jsonify({"status": "error", "message": "No rotation provided"}), 400
    image_path = utils.secure_path(image_path)

    file_extension = utils.get_file_extension(image_path)
    if file_extension not in {'jpg', 'jpeg'}:
        return jsonify({"status": "error", "message": "Rotation is only supported for JPG/JPEG images"}), 400
    if rotation % 90 != 0:
        return jsonify({"status": "error", "message": "Invalid rotation. Must be 90, 180, or 270"}), 400

    abs_path = filesystem.key_to_abs_path(image_path)
    if not os.path.exists(abs_path):
        return jsonify({"status": "error", "message": "Image not found"}), 404

    album_path = os.path.dirname(image_path)
    filename = os.path.basename(image_path)

    # Treating the rotate as a MOVE, we can do this by only regerating the UUID portion of the filename.
    new_filename = utils.regenerate_uuid_of_filename(filename)
    new_image_path = f'{album_path}/{new_filename}'
    new_abs_path = filesystem.key_to_abs_path(new_image_path)

    shutil.copy(abs_path, new_abs_path)
    exit_code = utils.rotate_jpg_by_degree(new_abs_path, rotation)

    if exit_code != 0:
        filesystem.silentremove(new_abs_path)
        return jsonify({"status": "error", "message": "Failed to rotate image"}), 500

    s3_ping_url = config()['url']['s3_ping_url'].as_str()
    offline_events_file = config()['paths']['offline_events_file'].as_str()

    if not aws.ping(s3_ping_url):
        offline_events = [offline.create_offline_event('MOVE', abs_path, new_abs_path)]
        offline.save_offline_events(offline_events_file, offline_events)
    else:
        success, failure = cloud_client().move_bulk([(image_path, new_image_path)])
        print(f"[DEBUG] Success: {success}, Failure: {failure}")
        if failure:
            print(f"Failed to upload rotated image to cloud: {failure}")
            filesystem.silentremove(new_abs_path)
            return jsonify({"status": "error", "message": "Failed to upload rotated image to cloud"}), 500
        message = json.dumps({
            "events": [{"event": "MOVE", "path": image_path, "newPath": new_image_path}],
            "sender": os.getenv('USERNAME')
        })
        cloud_client().insert_queue(message)

    filesystem.silentremove(abs_path)
    return jsonify({"status": "ok", "newPath": new_image_path})