import os
import json
import random
import subprocess

from app.config.config import config

slideshow_proc: subprocess.Popen | None = None

def start_slideshow(album: str, blend: int, speed: int):
    """
    Start the slideshow with the given settings.

    album: str - The path to the album to display.
    blend: int - The blend time between images in milliseconds.
    speed: int - The time each image is displayed in seconds.
    """
    global slideshow_proc

    active_slideshow = config()['paths']['active_slideshow_file'].as_str()
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "display_slideshow.sh")
    cmd = [script_path, album, str(speed), str(blend), active_slideshow]
    slideshow_proc = subprocess.Popen(cmd)

def stop_slideshow():
    global slideshow_proc

    if slideshow_proc is not None:
        # Killing the script doesn't seem to trigger the cleanup in the script, so we need to kill fbi explicitly.
        os.system(f"pkill -15 -f display_slideshow.sh")
        os.system(f"pkill -15 -f fbi")
        slideshow_proc.terminate()
        slideshow_proc.wait()

def load_settings():
    settings_file = config()['paths']['settings_file'].as_str()
    default_settings = {
        "album": config()['default_settings']['album'].as_str(),
        "isEnabled": config()['default_settings']['isEnabled'].as_bool(),
        "blend": config()['default_settings']['blend'].as_int(),
        "speed": config()['default_settings']['speed'].as_int(),
        "randomize": config()['default_settings']['randomize'].as_bool()
    }

    if not os.path.exists(settings_file):
        return default_settings

    with open(settings_file, 'r') as f:
        return json.load(f)

# Expects a dictionary of settings.
def save_settings_to_file(settings):
    settings_file = config()['paths']['settings_file'].as_str()
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

def set_image_order(album: str, randomize:bool, recursive: bool):
    file_names: list[str] = []
    
    for root, dirs, files in os.walk(album):
        # sorts by increasing modification time
        file_names.extend(sorted([os.path.join(root, file) for file in files], key=os.path.getmtime))
        if not recursive:
            break

    if randomize:
        random.shuffle(file_names)

    active_slideshow_file = config()['paths']['active_slideshow_file'].as_str()
    with open(active_slideshow_file, 'w') as f:
        f.write('\n'.join(file_names))