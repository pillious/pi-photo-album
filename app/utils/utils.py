import subprocess
import os
import uuid
from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

### General Utils
def clamp(val, min, max):
    return max if val > max else min if val < min else val

def get_file_extension(filename: str):
    return filename.rsplit('.', 1)[1].lower()

def regenerate_uuid_of_filename(filename: str) -> str:
    """
    Regenerate the UUID of a filename, preserving the user-facing part.

    Format: <uuid>.<user-facing-name>.<ext>

    Args:
        filename (str): The original filename with UUID prefix

    Returns:
        str: New filename with a new UUID but same user-facing part
    """
    first_dot_index = filename.index('.')
    user_facing_name = filename[first_dot_index + 1:]
    return f'{uuid.uuid4()}.{user_facing_name}'

def handle_duplicate_file(folder: str, name: str):
    """
    If the file already exists, convert to a unique name with format "*_int".
     """
    loc = f"{folder}/{name}"
    if os.path.exists(loc):
        name_parts = name.rsplit('.', 1)
        count = 1
        while os.path.exists(f"{folder}/{name_parts[0]}_{count}.{name_parts[1]}"):
            count += 1
        loc = f"{folder}/{name_parts[0]}_{count}.{name_parts[1]}"
    return loc

def heif_to_jpg(heif_path, jpg_path, quality:int):
    """
    Convert a HEIF/HEIC file to JPG using the `heif-convert` command.
    """
    os.makedirs(os.path.dirname(heif_path), exist_ok=True)
    os.makedirs(os.path.dirname(jpg_path), exist_ok=True)
    # TODO: this isn't really necessary anymore
    jpg_path_new = handle_duplicate_file(os.path.dirname(jpg_path), os.path.basename(jpg_path))
    proc = subprocess.Popen(["heif-convert", "-q", str(quality), heif_path, jpg_path_new])
    return proc

def heifs_to_jpgs(heif_paths: list[str], jpg_paths: list[str], quality: int, cleanup: bool):
    """
    Convert multiple HEIF/HEIC files to JPG in parallel.
    """
    procs: list[subprocess.Popen[bytes]] = []

    for heif_path, jpg_path in zip(heif_paths, jpg_paths):
        proc = heif_to_jpg(heif_path, jpg_path, quality)
        procs.append(proc)
    exit_codes = [proc.wait() for proc in procs]

    if cleanup:
        for heif_path in heif_paths:
            os.remove(heif_path)

    return exit_codes

def rotate_jpg(jpg_path):
    """
    Rotate a JPG file to horizontal based on its EXIF orientation.
    """
    os.makedirs(os.path.dirname(jpg_path), exist_ok=True)
    proc = subprocess.Popen(["exiftran", "-i", "-a", jpg_path])
    return proc

def rotate_jpgs(jpg_paths: list[str]):
    """
    Rotate JPG files in parallel.
    """
    procs = []
    for jpg_path in jpg_paths:
        proc = rotate_jpg(jpg_path)
        procs.append(proc)
    exit_codes = [proc.wait() for proc in procs]
    return exit_codes

def rotate_jpg_by_degree(jpg_path: str, degree: int):
    """
    Rotate a JPG file by a 90,180, or 270 degree clockwise.
    """
    if degree % 90 != 0:
        raise ValueError("Degree must be a multiple of 90 degrees.")

    rotation_flag = "" # exiftran flag for rotation
    match degree % 360:
        case 0:
            return 0
        case 90:
            rotation_flag = "-9"
        case 180:
            rotation_flag = "-1"
        case 270:
            rotation_flag = "-2"

    os.makedirs(os.path.dirname(jpg_path), exist_ok=True)
    proc = subprocess.Popen(["exiftran", "-i", rotation_flag, jpg_path])
    exit_code = proc.wait()
    return exit_code

def save_image_to_disk(album_path: str, image_name: str, image: FileStorage, handle_duplicates: bool) -> str:
    loc = f"{album_path}/{image_name}"
    if handle_duplicates:
        loc = handle_duplicate_file(album_path, image_name)
    os.makedirs(album_path, exist_ok=True)
    image.save(loc)
    return loc

def partial_dict_merge(d: dict, u: dict):
    """
    Performs a deep merge on `d` to include all keys from `u` that are not already in `d`.
    """
    for k, v in u.items():
        if k in d and isinstance(d[k], dict) and isinstance(v, dict):
            partial_dict_merge(d[k], v)
        elif k not in d:
            d[k] = v
    return d

def load_env(dirs: list[str]):
    for d in dirs:
        d = os.path.abspath(os.path.expandvars(d))
        if os.path.exists(d):
            load_dotenv(d)
            print(f"Loaded env vars from {d}.")
            return

    print(f"Failed to load env vars from {dirs}.")

def secure_path(path: str) -> str:
    return "/".join([secure_filename(p) for p in path.split('/')])

