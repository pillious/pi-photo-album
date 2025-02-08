from flask import Flask, render_template, request, jsonify
import json
import os
from dotenv import load_dotenv

import slideshow
import utils

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024 # 128MB
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.webp', '.heif', '.heic']

base_dir = os.path.abspath(os.path.expandvars("$HOME/pi-photo-album"))
user_dir = "alee1246"
shared_dir = "shared"

def enforce_mime(mime_type):
    def decorator(func):
        def wrapper(*args, **kwargs):
            content_type = request.content_type
            if content_type.split(';')[0] != mime_type:
                return jsonify({"status": "error", "message": f"Invalid content type. Expected {mime_type}."}), 400
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', settings=slideshow.load_settings())

@app.route('/save-settings', methods=['POST'])
@enforce_mime('application/json')
def save_settings():
    settings = request.json

    # Some settings validation
    if 'isEnabled' not in settings or type(settings["isEnabled"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for isEnabled"}), 400
    if 'blend' not in settings or type(settings["blend"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for blend"}), 400
    if 'speed' not in settings or type(settings["speed"]) is not int:
        return jsonify({"status": "error", "message": "Invalid value for speed"}), 400
    if 'randomize' not in settings or type(settings["randomize"]) is not bool:
        return jsonify({"status": "error", "message": "Invalid value for randomize"}), 400

    cleanedSettings = {
        "isEnabled": settings["isEnabled"],
        "blend": utils.clamp(settings["blend"], 0, 1000),
        "speed": utils.clamp(settings["speed"], 0, 180),
        "randomize": settings["randomize"]
    }

    print(cleanedSettings)
    slideshow.save_settings_to_file(cleanedSettings)

    # Update display with the new settings.
    print(slideshow.stop_slideshow())
    if cleanedSettings["isEnabled"]:
        print(slideshow.start_slideshow("~/albums/nature", cleanedSettings["blend"], cleanedSettings["speed"], cleanedSettings["randomize"]))

    return jsonify({"status": "ok"})

@app.route('/upload-images', methods=['POST'])
@enforce_mime('multipart/form-data')
def upload_images():
    if 'file' not in request.files: 
        return jsonify({"status": "error", "message": "No images uploaded"}), 400

    # TODO: I think I can determine which album to put the file in by looking at the key
    # Use request.files.keys()
    # getList of keys should give all the files added to the same album.
    # I can tell if it's a shared file if the key starts with shared/
    images = request.files.getlist('file')
    for image in images:
        print(image.filename)
        print( utils.get_file_extension(image.filename))
        # image.save(f'./uploads/{image.filename}')

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')