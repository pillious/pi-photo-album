from flask import Flask, render_template, request, jsonify
import json
import os

from utils import clamp

app = Flask(__name__)

settings_file = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/settings.json'))
default_settings = {
    "isEnabled": True, 
    "blend": 250, 
    "speed": 30, 
    "randomize": False
}

@app.route('/')
def index():
    return render_template('index.html', settings=load_settings())

@app.route('/save-settings', methods=['POST'])
def save_settings():
    settings = request.json

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
        "blend": clamp(settings["blend"], 0, 1000),
        "speed": clamp(settings["speed"], 0, 180),
        "randomize": settings["randomize"]
    }

    print(cleanedSettings) ### DEBUG
    save_settings(cleanedSettings)

    # TODO: Implement these functions
    # restartSlideshow()
    # startSlideshow()

    return jsonify({"status": "ok"})

def load_settings():
    if not os.path.exists(settings_file):
        return default_settings

    with open(settings_file, 'r') as f:
        return json.load(f)
    
def save_settings(settings):
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')