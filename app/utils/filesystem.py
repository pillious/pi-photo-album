import os

from app.config.config import config

def get_default_file_structure(username: str):
    return {
        "albums": {
            username: {},
            "Shared": {}
        }
    }

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

def is_file_owner(file_path: str):
    """
    Check if the file path can be accessed by the current user.

    file_path can optionally include the prefix "albums/".
    """
    if file_path.startswith('albums/'):
        file_path = file_path[7:]
    allowed_prefixes = config()['files']['allowed_prefixes'].as_set().as_strs()
    return file_path.split('/', 1)[0] in allowed_prefixes

def list_files_in_dir(dir_path: str, allowed_prefixes: list[str] = []):
    """
    List all files in a directory and its subdirectories.
    If `allowed_prefixes` is provided, only include files in those subdirectories.
    """
    file_list = []
    for root, dirs, files in os.walk(dir_path):
        root = root.replace(dir_path + "/", "")
        if not allowed_prefixes or any(root.startswith(prefix) for prefix in allowed_prefixes):
            for file in files:
                file_list.append(os.path.join(root, file))
    return file_list

def key_to_abs_path(key: str):
    """
    Converts a `key` of the format "albums/..." to the abs path on the local system.
    
    `key` is the path stored on the cloud.
    """
    return f'{config()["paths"]["base_dir"].as_str()}/{key}'

def strip_base_dir(abs_path: str):
    return abs_path.removeprefix(f"{config()['paths']['base_dir'].as_str()}/")

def silentremove(path: str):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

def remove_albums_prefix(path: str):
    """
    Removes the 'albums/' prefix from the path if it exists.
    """
    return path.removeprefix('albums/')

def remove_dirs(base: str, path: str):
    """
    Removes all empty dirs in the path, up to the base directory.

    - base format: `abs(.../.../albums)`
    - path format: `[Shared|username]/.../.../<folder>`

    This won't remove the [Shared|username] folder even if it is empty.
    """
    dirs = path.split('/')
    first = dirs.pop(0)
    while len(dirs) > 0:
        try:
            os.rmdir(os.path.join(base, first, '/'.join(dirs)))
        except Exception:
            break
        dirs.pop()
