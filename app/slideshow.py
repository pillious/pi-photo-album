import os
import json

import app.globals as globals

def start_slideshow(album: str, blend: int, speed: int, randomize: bool):
    """
    Start the slideshow with the given settings.

    album: str - The path to the album to display.
    blend: int - The blend time between images in milliseconds.
    speed: int - The time each image is displayed in seconds.
    randomize: bool - Whether to display images in a random order.
    """

    photos = f"{album}/*"
    cmd = ["sudo", "fbi", "-d", "/dev/fb0", "-T", "1", "-noverbose", "-readahead", "-a", photos, "-t", str(speed), "-blend", str(blend)]

    if randomize:
        cmd.append("-u")

    print(' '.join(cmd))
    return os.system(' '.join(cmd))

def stop_slideshow():
    cmd = "sudo killall -15 fbi"
    print(cmd)
    return os.system(cmd)

def load_settings():
    if not os.path.exists(globals.SETTINGS_FILE):
        return globals.DEFAULT_SETTINGS

    with open(globals.SETTINGS_FILE, 'r') as f:
        return json.load(f)

# Expects a dictionary of settings.
def save_settings_to_file(settings):
    os.makedirs(os.path.dirname(globals.SETTINGS_FILE), exist_ok=True)
    with open(globals.SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)