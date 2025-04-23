import os

DEFAULT_SETTINGS = {
    "album": "Shared",
    "isEnabled": True, 
    "blend": 250, 
    "speed": 30, 
    "randomize": False
}

SETTINGS_FILE = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/settings.json'))

BASE_DIR = os.path.abspath(os.path.expandvars("$HOME/pi-photo-album"))
TMP_STORAGE = BASE_DIR + "/tmp"

MAX_CONTENT_LENGTH = 128 * 1024 * 1024 # 128MB
ALLOWED_FILE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'}

ALLOWED_PREFIXES = {'Shared', os.getenv('USERNAME')} if os.getenv('USERNAME') else {'Shared'}