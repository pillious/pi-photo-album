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