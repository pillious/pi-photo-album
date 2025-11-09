import os
from pathlib import Path

def create_fs(root: Path, fs: dict):
    def _create_fs(path, tree):
        for name, content in tree.items():
            current_path = os.path.join(path, name)
            if isinstance(content, dict):
                os.mkdir(current_path)
                _create_fs(current_path, content)
            else:
                with open(current_path, "w") as _:
                    pass

    os.makedirs(root, exist_ok=True)            
    _create_fs(root, fs)

def dict_fs_to_list(dict_fs: dict, prefix: str = "") -> list[str]:
    """
    Converts a nested dict representation of a filesystem to a flat list of file paths.
    """
    file_list = []

    def _dict_fs_to_list(d: dict, curr_path: str):
        for name, content in d.items():
            new_path = os.path.join(curr_path, name) if curr_path else name
            if isinstance(content, dict):
                _dict_fs_to_list(content, new_path)
            else:
                file_list.append(new_path)

    if prefix:
        prefix_parts = prefix.strip('/').split("/")
        for part in prefix_parts:
            try:
                dict_fs = dict_fs[part]
            except KeyError:
                raise ValueError(f"Prefix '{prefix}' not found.")

    _dict_fs_to_list(dict_fs, prefix)
    return file_list