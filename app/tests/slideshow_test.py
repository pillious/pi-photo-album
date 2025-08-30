import os
import time
import random
from pathlib import Path
from unittest.mock import patch, MagicMock

from app import slideshow
from app.config import config
from app.tests import utils

class TestSlideshow:
    @patch("app.slideshow.subprocess.Popen")
    def test_start_slideshow(self, mock_popen):
        c = {"paths": {"active_slideshow_file": "base/active_slideshow.txt"}}
        config.load_config(c)

        script_path = os.path.join(os.path.dirname(os.path.abspath(Path(__file__).parent)), "display_slideshow.sh")
        album = "a/b/test_album"
        blend = 500
        speed = 5
        slideshow.start_slideshow(album, blend, speed)

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]  # Get the first positional argument (the command list)
        assert args[0] == script_path
        assert args[1] == album
        assert args[2] == str(speed)
        assert args[3] == str(blend)
        assert args[4] == c["paths"]["active_slideshow_file"]

    @patch("app.slideshow.os.system")
    @patch("app.slideshow.slideshow_proc", create=True)
    def test_stop_slideshow(self, mock_slideshow_proc, mock_os_system):
        # Simulate a running process
        mock_process = MagicMock()
        mock_slideshow_proc.terminate = mock_process.terminate
        mock_slideshow_proc.wait = mock_process.wait

        slideshow.stop_slideshow()

        mock_os_system.assert_any_call("pkill -15 -f display_slideshow.sh")
        mock_os_system.assert_any_call("pkill -15 -f fbi")
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_load_default_settings(self):
        c = {
            "paths": {"settings_file": "non_existent_file.json"},
            "default_settings": {
                "album": "a/b/c",
                "isEnabled": False,
                "blend": 500,
                "speed": 5,
                "randomize": False
            }
        }
        config.load_config(c)
        assert slideshow.load_settings() == c["default_settings"]

    def test_load_settings(self, tmp_path: Path):
        c = {
            "paths": {"settings_file": tmp_path / "settings.json"},
        }
        config.load_config(c)
        settings = {
            "album": "Shared/imgs",
            "isEnabled": True,
            "blend": 250,
            "speed": 30,
            "randomize": True
        }
        slideshow.save_settings_to_file(settings)
        assert slideshow.load_settings() == settings

    def test_set_image_order(self, tmp_path: Path):
        c = {"paths": {"active_slideshow_file": tmp_path / "active_slideshow.txt"}}
        config.load_config(c)
        fs = {
            "albums": {
                "Shared": {
                    "a": {},
                    "b": {"image4.jpg": ""}
                }
            }
        }
        utils.create_fs(tmp_path, fs)
        images = [
            "albums/Shared/a/image1.jpg",
            "albums/Shared/a/image2.jpg",
            "albums/Shared/a/image3.jpg"
        ]
        for img in images:
            with open(tmp_path / img, "w") as f:
                f.write("")
            time.sleep(0.01)

        album = tmp_path / "albums" / "Shared" / "a"
        slideshow.set_image_order(str(album), False, False)

        with open(c["paths"]["active_slideshow_file"], "r") as f:
            image_order = f.readlines()
        assert len(image_order) == len(images)
        for img, img_o in zip(images, image_order):
            assert img_o.strip().removeprefix(f"{tmp_path}/") == img

    def test_image_order_randomize(self, tmp_path: Path):
        c = {"paths": {"active_slideshow_file": tmp_path / "active_slideshow.txt"}}
        config.load_config(c)
        fs = {
            "albums": {
                "Shared": {
                    "a": {},
                    "b": {"image4.jpg": ""}
                }
            }
        }
        utils.create_fs(tmp_path, fs)
        images = [
            "albums/Shared/a/image1.jpg",
            "albums/Shared/a/image2.jpg",
            "albums/Shared/a/image3.jpg"
        ]
        for img in images:
            with open(tmp_path / img, "w") as f:
                f.write("")
            time.sleep(0.01)

        album = tmp_path / "albums" / "Shared" / "a"
        random.seed(1)
        slideshow.set_image_order(str(album), True, False)

        with open(c["paths"]["active_slideshow_file"], "r") as f:
            image_order = f.readlines()
        random.seed(1)    
        random.shuffle(images)
        assert len(image_order) == len(images)
        for img, img_o in zip(images, image_order):
            assert img_o.strip().removeprefix(f"{tmp_path}/") == img

    def test_set_image_order_recursive(self, tmp_path: Path):
        c = {"paths": {"active_slideshow_file": tmp_path / "active_slideshow.txt"}}
        config.load_config(c)
        fs = {
            "albums": {
                "Shared": {
                    "a": {"b": {}, "c": {}},
                    "b": {"image4.jpg": ""}
                }
            }
        }
        utils.create_fs(tmp_path, fs)
        images = [
            "albums/Shared/a/image1.jpg",
            "albums/Shared/a/b/image1.jpg",
            "albums/Shared/a/c/image1.jpg",
            "albums/Shared/a/image2.jpg",
            "albums/Shared/a/b/image2.jpg",
            "albums/Shared/a/c/image2.jpg",
            "albums/Shared/a/image3.jpg"
        ]
        # sort by increasing length, then alphabetically.
        expected_order = sorted(images, key=lambda x: (len(x),x)) 
        for img in images:
            with open(tmp_path / img, "w") as f:
                f.write("")
            time.sleep(0.01)

        album = tmp_path / "albums" / "Shared" / "a"
        slideshow.set_image_order(str(album), False, True)

        with open(c["paths"]["active_slideshow_file"], "r") as f:
            image_order = f.readlines()
        assert len(image_order) == len(images)
        for img, img_o in zip(expected_order, image_order):
            assert img_o.strip().removeprefix(f"{tmp_path}/") == img