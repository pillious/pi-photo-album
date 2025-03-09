import subprocess
from typing import List
import os
from werkzeug.datastructures import FileStorage


def clamp(val, min, max):
    return max if val > max else min if val < min else val

def get_file_extension(filename: str):
    return filename.rsplit('.', 1)[1].lower()

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

def multiple_heif_to_jpg(heif_paths: List[str], jpg_paths: List[str], quality: int, cleanup: bool):
    """
    Convert multiple HEIF/HEIC files to JPG in parallel using the `heif-convert` command.
    """
    procs: List[subprocess.Popen[bytes]] = []

    for heif_path, jpg_path in zip(heif_paths, jpg_paths):
        os.makedirs(os.path.dirname(heif_path), exist_ok=True)
        os.makedirs(os.path.dirname(jpg_path), exist_ok=True)
        # TODO: this isn't really necessary anymore
        jpg_path_new = handle_duplicate_file(os.path.dirname(jpg_path), os.path.basename(jpg_path))
        proc = subprocess.Popen(["heif-convert", "-q", str(quality), heif_path, jpg_path_new])
        procs.append(proc)

    exit_codes = [proc.wait() for proc in procs]

    if cleanup:
        for heif_path in heif_paths:
            os.remove(heif_path)

    return exit_codes

def save_image_to_disk(album_path: str, image_name: str, image: FileStorage) -> str:
    loc = handle_duplicate_file(album_path, image_name)
    os.makedirs(album_path, exist_ok=True)
    image.save(loc)
    return loc

def get_file_structure(root_dir: str):
    """
    Generate a dictionary representing a file structure.
    """
    dir_dict = {}
    root_dir = root_dir.rstrip(os.sep)
    start = root_dir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(root_dir):
        folders = path[start:].split(os.sep)
        subdir = {file: "" for file in files}
        parent = dir_dict
        for folder in folders[:-1]:
            parent = parent.setdefault(folder, {})
        parent[folders[-1]] = subdir
    return dir_dict