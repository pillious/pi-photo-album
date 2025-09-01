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

def upload_images(request: Request):
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
                heif_files.append((guid, image_name))
                image.save(f"{tmp_storage_dir}/{image_name}")
            else:
                loc = utils.save_image_to_disk(f'{base_dir}/albums/{album_path}', image_name, image, True)
                saved_files.append((guid, loc))

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [f"{base_dir}/albums/{os.path.dirname(heif_file[1])}/{heif_file[1].rsplit('.', 1)[0]}.jpg" for heif_file in heif_files]
        heif_paths = [f"{tmp_storage_dir}/{heif_file[1]}" for heif_file in heif_files]
        exit_codes = utils.heifs_to_jpgs(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            saved_files.append((heif_files[i][0], jpg_paths[i])) if code == 0 else failed_files.append(heif_files[i][0])

    # Parallelize the rotation of JPG files.
    jpg_paths = [sf[1] for sf in saved_files if utils.get_file_extension(sf[1]) in {'jpg', 'jpeg'}]
    if len(jpg_paths) > 0:
        utils.rotate_jpgs(jpg_paths)

    if not aws.ping(config()['url']['s3_ping_url'].as_str()):
        offline_events = [offline.create_offline_event('PUT', sf[1]) for sf in saved_files]
        offline_events_file = config()['paths']['offline_events_file'].as_str()
        offline.save_offline_events(offline_events_file, offline_events)
    elif len(saved_files) > 0:
        # Bulk upload to cloud
        success, failure = cloud_client().insert_bulk([sf[1] for sf in saved_files], [filesystem.strip_base_dir(sf[1]) for sf in saved_files])
        failed_files = failed_files + [sf[0] for sf in saved_files if filesystem.strip_base_dir(sf[1]) in failure]

        # Push events to queue
        message = json.dumps({"events": [{"event": "PUT", "path": sf} for sf in success], "sender": os.getenv('USERNAME')})
        cloud_client().insert_queue(message)

    # failed: the guids of the files that failed to upload.
    # success: the paths of the files that were successfully uploaded.
    # return jsonify({"status": "ok", "failed": failed_files, "success": success})
    print(f'failed to upload: {failed_files}')
    return jsonify({"status": "ok", "failed": [], "success": [filesystem.strip_base_dir(sf[1]) for sf in saved_files]})

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