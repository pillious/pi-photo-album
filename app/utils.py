import subprocess
from typing import List
import os
from werkzeug.datastructures import FileStorage
import boto3
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session


### General Utils
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

def save_image_to_disk(album_path: str, image_name: str, image: FileStorage, handle_duplicates: bool) -> str:
    loc = f"{album_path}/{image_name}"
    if handle_duplicates:
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

def get_default_file_structure(username: str):
    return {
        "albums": {
            username: {},
            "Shared": {}
        }
    }

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

### AWS Session Utils
def get_aws_autorefresh_session(aws_role_arn, session_name):
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata = get_aws_credentials(aws_role_arn, session_name),
        refresh_using = lambda: get_aws_credentials(aws_role_arn, session_name),
        method = 'sts-assume-role'
    )

    session = get_session()
    session._credentials = session_credentials
    autorefresh_session = boto3.Session(botocore_session=session)

    return autorefresh_session, session_credentials

def get_aws_credentials(aws_role_arn, session_name):
        sts_client = boto3.client('sts')
        assumed_role_object = sts_client.assume_role(
            RoleArn = aws_role_arn,
            RoleSessionName = session_name,
            DurationSeconds = 900
        )
        return {
            'access_key': assumed_role_object['Credentials']['AccessKeyId'],
            'secret_key': assumed_role_object['Credentials']['SecretAccessKey'],
            'token': assumed_role_object['Credentials']['SessionToken'],
            'expiry_time': assumed_role_object['Credentials']['Expiration'].isoformat()
        }