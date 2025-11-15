import os
from flask import Flask, request, jsonify

from app import slideshow
from app.announcer import init_event_announcer
from app.cloud_clients.cloud_client import init_cloud_client
from app.cloud_clients.aws_client import new_aws_client
from app.config.config import config, load_config
from app.utils import utils
from app.routes import \
    slideshow as slideshow_routes, \
    filesystem as filesystem_routes, \
    template as template_routes, \
    event as event_routes

app = Flask(__name__)

utils.load_env([".env", os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/.env'))])
load_config()
init_cloud_client(new_aws_client())
init_event_announcer()

app.config['MAX_CONTENT_LENGTH'] = config()['files']['max_content_length'].as_int()

def enforce_mime(mime_type):
    def decorator(func):
        def wrapper(*args, **kwargs):
            content_type = request.content_type
            if not content_type or content_type.split(';')[0] != mime_type:
                return jsonify({"status": "error", "message": f"Invalid content type. Expected {mime_type}."}), 400
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

@app.route('/', methods=['GET'])
def index():
    return template_routes.index()

@app.route('/save-settings', methods=['POST'])
@enforce_mime('application/json')
def save_settings():
    return slideshow_routes.save_settings(request)

@app.route('/shuffle', methods=['POST'])
def shuffle():
    return slideshow_routes.shuffle()

@app.route('/upload-images', methods=['POST'])
@enforce_mime('multipart/form-data')
def upload_images():
    return filesystem_routes.upload_images(request)

@app.route('/delete-images', methods=['POST'])
@enforce_mime('application/json')
def delete_images():
    return filesystem_routes.delete_images(request)

@app.route('/move-images', methods=['POST'])
@enforce_mime('application/json')
def move_images():
    return filesystem_routes.move_images(request)

@app.route('/copy-images', methods=['POST'])
@enforce_mime('application/json')
def copy_images():
    return filesystem_routes.copy_images(request)

@app.route('/receive-events', methods=['POST'])
@enforce_mime('application/json')
def receive_events():
    return event_routes.receive_events(request)

@app.route('/stream-events', methods=['GET'])
def stream_events():
    return event_routes.stream_events()

@app.route('/resync', methods=['POST'])
def resync():
    return event_routes.resync()

@app.route('/preview', methods=['GET'])
def preview():
    return filesystem_routes.preview(request)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    base_dir = config()['paths']['base_dir'].as_str()
    tmp_storage_dir = config()['paths']['tmp_storage_dir'].as_str()

    os.makedirs(tmp_storage_dir, exist_ok=True)
    os.makedirs(config()['paths']['config_dir'].as_str(), exist_ok=True)
    os.makedirs(f"{base_dir}/albums", exist_ok=True)
    os.makedirs(tmp_storage_dir, exist_ok=True)

    # Starts slideshow on startup if it's enabled in the settings.
    settings = slideshow.load_settings()
    if settings["isEnabled"]:
        album_path = f"{base_dir}/albums/{settings['album']}"
        slideshow.start_slideshow(album_path, settings["blend"], settings["speed"])

    # Disable debug mode and reloader in production
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', use_reloader=debug_mode, port=int(os.getenv('API_PORT', 5555)))
