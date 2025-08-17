from flask import jsonify, Request
import time

from app import slideshow
from app.utils import utils
from app.config.config import config

def save_settings(request: Request):
    settings: dict | None = request.json
    if not settings:
        return jsonify({"status": "ok"})

    # Some settings validation
    if 'album' not in settings or type(settings["album"]) is not str:
        return jsonify({"status": "error", "message": "Invalid value for album"}), 400
    if 'isEnabled' not in settings or type(settings["isEnabled"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for isEnabled"}), 400
    if 'blend' not in settings or type(settings["blend"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for blend"}), 400
    if 'speed' not in settings or type(settings["speed"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for speed"}), 400
    if 'randomize' not in settings or type(settings["randomize"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for randomize"}), 400

    prev_settings = slideshow.load_settings()

    cleaned_settings = {
        "album": settings["album"],
        "isEnabled": settings["isEnabled"],
        "blend": utils.clamp(settings["blend"], 0, 1000),
        "speed": utils.clamp(settings["speed"], 0, 180),
        "randomize": settings["randomize"],
    }

    slideshow.save_settings_to_file(cleaned_settings)
    slideshow.stop_slideshow()

    base_dir = config()['paths']['base_dir'].as_str()
    album_path = f"{base_dir}/albums/{cleaned_settings['album']}"
    if (cleaned_settings["randomize"] != prev_settings["randomize"]
        or cleaned_settings["album"] != prev_settings["album"]):
        # Must be set to recursive b/c inotifywait is setup to watch recursively.
        slideshow.set_image_order(album_path, cleaned_settings["randomize"], True)
    if cleaned_settings["isEnabled"]:
        time.sleep(1)
        slideshow.start_slideshow(album_path, cleaned_settings["blend"], cleaned_settings["speed"])

    return jsonify({"status": "ok"})

def shuffle():
    settings = slideshow.load_settings()
    if settings["album"]:
        base_dir = config()['paths']['base_dir'].as_str()
        album_path = f"{base_dir}/albums/{settings['album']}"
        # Must be set to recursive b/c inotifywait is setup to watch recursively.
        slideshow.set_image_order(album_path, True, True)
        if settings["isEnabled"]:
            slideshow.stop_slideshow()
            time.sleep(1)
            slideshow.start_slideshow(album_path, settings["blend"], settings["speed"])
    return jsonify({"status": "ok"})