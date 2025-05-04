import os

DEFAULT_SETTINGS = {
    "album": "Shared",
    "isEnabled": True, 
    "blend": 250, 
    "speed": 30, 
    "randomize": False
}

CONFIG_DIR = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album'))
SETTINGS_FILE = CONFIG_DIR + "/settings.json"
LAST_POLL_FILE = CONFIG_DIR + "/last_poll.txt"
FS_SNAPSHOT_FILE = CONFIG_DIR + "/fs_snapshot.json"
OFFLINE_EVENTS_FILE = CONFIG_DIR + "/events.csv"

BASE_DIR = os.path.abspath(os.path.expandvars("$HOME/pi-photo-album"))
TMP_STORAGE_DIR = BASE_DIR + "/tmp"

MAX_CONTENT_LENGTH = 128 * 1024 * 1024 # 128MB
ALLOWED_FILE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'}

ALLOWED_PREFIXES = {'Shared', os.getenv('USERNAME')} if os.getenv('USERNAME') else {'Shared'}

QUEUE_RETENTION_DAYS = 4