from flask import render_template
import os

from app import slideshow
from app.utils import filesystem, utils
from app.config.config import config

def index():
    settings = slideshow.load_settings()
    username = os.getenv('USERNAME')
    if not username:
        raise ValueError("Environment variable 'USERNAME' must be set.")
    default_file_structure = filesystem.get_default_file_structure(username)
    base_dir = config()['paths']['base_dir'].as_str()
    file_structure = filesystem.get_file_structure(f"{base_dir}/albums")

    # Ensure that the default file structure is always present at a minimum.
    file_structure = utils.partial_dict_merge(file_structure, default_file_structure)
    return render_template('index.html', settings=settings, fileStructure=file_structure)