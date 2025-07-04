import os

DEFAULT_SETTINGS = {
    "album": "Shared",
    "isEnabled": False, 
    "blend": 250, 
    "speed": 30, 
    "randomize": False
}

CONFIG_DIR = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album'))
SETTINGS_FILE = CONFIG_DIR + "/settings.json"
ENV_FILE = CONFIG_DIR + "/.env"
LAST_POLL_FILE = CONFIG_DIR + "/last_poll.txt"
FS_SNAPSHOT_FILE = CONFIG_DIR + "/fs_snapshot.json"
OFFLINE_EVENTS_FILE = CONFIG_DIR + "/events.csv"
ACTIVE_SLIDESHOW_FILE = CONFIG_DIR + "/active_slideshow.txt"

BASE_DIR = os.path.abspath(os.path.expandvars("$HOME/pi-photo-album"))
TMP_STORAGE_DIR = BASE_DIR + "/tmp"

MAX_CONTENT_LENGTH = 128 * 1024 * 1024 # 128MB
ALLOWED_FILE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'}

ALLOWED_PREFIXES = {'Shared', os.getenv('USERNAME')} if os.getenv('USERNAME') else {'Shared'}

QUEUE_RETENTION_DAYS = 4

API_URL = f"http://localhost:{os.getenv('API_PORT', 5000)}"
SQS_PING_URL = f"https://sqs.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/ping"
S3_PING_URL = f"https://s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/ping"