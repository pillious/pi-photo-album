import os
import json
import random
import subprocess

import app.globals as globals

slideshow_proc: subprocess.Popen | None = None

def start_slideshow(album: str, blend: int, speed: int):
    """
    Start the slideshow with the given settings.

    album: str - The path to the album to display.
    blend: int - The blend time between images in milliseconds.
    speed: int - The time each image is displayed in seconds.
    """
    global slideshow_proc

    print(album, blend, speed)

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "display_slideshow.sh")
    cmd = [script_path, album, str(speed), str(blend), globals.ACTIVE_SLIDESHOW_FILE]
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
    if not os.path.exists(globals.SETTINGS_FILE):
        return globals.DEFAULT_SETTINGS

    with open(globals.SETTINGS_FILE, 'r') as f:
        return json.load(f)

# Expects a dictionary of settings.
def save_settings_to_file(settings):
    os.makedirs(os.path.dirname(globals.SETTINGS_FILE), exist_ok=True)
    with open(globals.SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def set_image_order(album: str, randomize:bool, recursive: bool):
    print(album, randomize, recursive)
    file_names: list[str] = []
    
    for root, dirs, files in os.walk(album):
        # sorts by increasing modification time
        file_names.extend(sorted([os.path.join(root, file) for file in files], key=os.path.getmtime))
        if not recursive:
            break

    if randomize:
        random.shuffle(file_names)

    print(file_names)
    with open(globals.ACTIVE_SLIDESHOW_FILE, 'w') as f:
        f.write('\n'.join(file_names))