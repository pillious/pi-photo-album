from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from cloud_adapters import s3_adapter
import slideshow
import utils
import globals

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024 # 128MB
app.config['UPLOAD_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'}

user_dir = "alee1246"
shared_dir = "Shared"

cloud_adapter = s3_adapter.S3Adapter('pi-photo-album-s3')

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
    settings = slideshow.load_settings()
    file_structure = utils.get_file_structure(f"{globals.BASE_DIR}/albums")
    if not file_structure:
        file_structure = globals.DEFAULT_FILE_STRUCTURE
    return render_template('index.html', settings=settings, fileStructure=file_structure)

@app.route('/save-settings', methods=['POST'])
@enforce_mime('application/json')
def save_settings():
    settings = request.json

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

    cleanedSettings = {
        "album": settings["album"],
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
    # TODO: I can tell if it's a shared file if the key starts with shared/
    saved_files = []
    failed_files = []
    heif_files = []

    # TEMP_SHARED = False

    print(request.files.keys())
    for album_path in request.files.keys():
        images = request.files.getlist(album_path)
        for image in images:
            print(album_path, secure_filename(image.filename))

            image_name = secure_filename(image.filename)
            file_extension = utils.get_file_extension(image_name)
            if file_extension not in app.config['UPLOAD_EXTENSIONS']:
                failed_files.append(image_name)
                continue

            if file_extension in {'heif', 'heic'}:
                heif_files.append(image_name)
                image.save(f"{globals.TMP_STORAGE}/{image_name}")
            else:
                loc = utils.save_image_to_disk(f'{globals.BASE_DIR}/albums/{album_path}', image_name, image)
                saved_files.append(loc)
                print(loc)

            # cloud = True
            # if cloud:
            #     prefix_len = len(f"{BASE_DIR}/album/")
            #     print(f"insert s3: {loc}, {loc[prefix_len:]}")
            #     # TODO: upload to cloud
            #     # TODO: also need to handle json file of the current state.
            #     # cloud_adapter.insert(loc, loc[prefix_len:])

    # Parallelize the conversion of HEIF files to JPG.
    if len(heif_files) > 0:
        jpg_paths = [f"{globals.BASE_DIR}/albums/{album_path}/{heif_file.rsplit('.', 1)[0]}.jpg" for heif_file in heif_files]
        heif_paths = [f"{globals.TMP_STORAGE}/{heif_file}" for heif_file in heif_files]
        exit_codes = utils.multiple_heif_to_jpg(heif_paths, jpg_paths, 80, True)
        for i, code in enumerate(exit_codes):
            saved_files.append(heif_files[i]) if code == 0 else failed_files.append(heif_files[i])
                
    # TODO: bulk upload to cloud.

    return jsonify({"status": "ok", "failed": failed_files})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')