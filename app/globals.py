import os

DEFAULT_SETTINGS = {
    "album": "alee1246/nature",
    "isEnabled": True, 
    "blend": 250, 
    "speed": 30, 
    "randomize": False
}


DEFAULT_FILE_STRUCTURE = {
    "alee1246": {},
    "Shared": {}
}

SETTINGS_FILE = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/settings.json'))

BASE_DIR = os.path.abspath(os.path.expandvars("$HOME/pi-photo-album"))
TMP_STORAGE = BASE_DIR + "/tmp"
# FS_STATE_FILE = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/fs_state.json'))

MAX_CONTENT_LENGTH = 128 * 1024 * 1024 # 128MB
ALLOWED_FILE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'}