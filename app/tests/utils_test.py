import base64
import os
import subprocess
import shutil
from pathlib import Path
from werkzeug.datastructures import FileStorage

from app.utils import utils

class TestUtils:
    def test_clamp(self):
        test_cases = [
            (5, 1, 10, 5),
            (0, 1, 10, 1),
            (15, 1, 10, 10),
        ]
        for x, min_val, max_val, expected in test_cases:
            assert utils.clamp(x, min_val, max_val) == expected

    def test_get_file_extension(self):
        test_cases = [
            ("image.jpg", "jpg"),
            ("image.123.png", "png"),
        ]
        for filename, expected in test_cases:
            assert utils.get_file_extension(filename) == expected

    def test_handle_duplicate_file(self, tmp_path):
        test_cases = [
            (tmp_path, "test.png", False, f"{tmp_path}/test.png"),
            (tmp_path, "image.jpg", True, f"{tmp_path}/image_1.jpg"),
            (f"{tmp_path}/a/b", "image_1_2.heif", True, f"{tmp_path}/a/b/image_1_2_1.heif")
        ]
        for folder, original, is_duplicate, expected in test_cases:
            if is_duplicate:
                os.makedirs(folder, exist_ok=True)
                open(f"{folder}/{original}", 'w')
            assert utils.handle_duplicate_file(folder, original) == expected

    def test_heif_to_jpg(self, tmp_path):
        heif_path = f"{Path(__file__).parent}/images/image.heif"
        proc = utils.heif_to_jpg(heif_path, f"{tmp_path}/output.jpg", quality=50)
        exit_code = proc.wait()
        assert exit_code == 0
        assert os.path.exists(f"{tmp_path}/output.jpg")

    def test_muliple_heif_to_jpg(self, tmp_path):
        heif_path = f"{Path(__file__).parent}/images/image.heif"
        heif_paths = [heif_path for _ in range(3)]
        jpg_paths = [f"{tmp_path}/output_{i}.jpg" for i in range(3)]

        # Test w/o Cleanup
        exit_codes = utils.heifs_to_jpgs(heif_paths, jpg_paths, quality=50, cleanup=False)
        for exit_code, jpg_path in zip(exit_codes, jpg_paths):
            assert exit_code == 0
            assert os.path.exists(jpg_path)

        # Test Cleanup:
        shutil.copy(heif_path, f"{tmp_path}/image.heif")
        exit_codes = utils.heifs_to_jpgs([f"{tmp_path}/image.heif"], [f"{tmp_path}/output_4.jpg"], quality=50, cleanup=True)
        assert exit_codes[0] == 0
        assert not os.path.exists(f"{tmp_path}/image.heif")
        assert os.path.exists(f"{tmp_path}/output_4.jpg")

    def test_rotate_jpg(self, tmp_path):
        test_img = f"{Path(__file__).parent}/images/rotate_90_cw.jpg"
        tmp_img = f"{tmp_path}/output.jpg"
        shutil.copy(test_img, tmp_img)
        proc = utils.rotate_jpg(tmp_img)
        proc.wait()
        self.verify_rotation(tmp_img)

    def test_rotate_jpgs(self, tmp_path):
        test_img = f"{Path(__file__).parent}/images/rotate_90_cw.jpg"
        files = [f"{tmp_path}/output_{i}.heif" for i in range(3)]
        for file in files:
            shutil.copy(test_img, file)
        utils.rotate_jpgs(files)
        for file in files:
            self.verify_rotation(file)

    def verify_rotation(self, jpg_path):
        proc = subprocess.Popen(
            ["exiftool", "-Orientation", "-n", "-s3", jpg_path],
            stdout=subprocess.PIPE,
            text=True
        )
        stdout, _ = proc.communicate()
        assert int(stdout.strip()) == 1

    def test_save_image_to_disk(self, tmp_path):
        with open(f"{tmp_path}/test.jpg", "wb") as f:
            f.write(b"test image data")
        image = FileStorage(stream=open(f"{tmp_path}/test.jpg", "rb"), filename="test.jpg")
        os.mkdir(f"{tmp_path}/a")
        
        utils.save_image_to_disk(f"{tmp_path}/a", "test.jpg", image, handle_duplicates=True)
        assert os.path.exists(f"{tmp_path}/a/test.jpg")

        utils.save_image_to_disk(f"{tmp_path}/a", "test.jpg", image, handle_duplicates=False)
        assert not os.path.exists(f"{tmp_path}/a/test_1.jpg") 

        utils.save_image_to_disk(f"{tmp_path}/a", "test.jpg", image, handle_duplicates=True)
        assert os.path.exists(f"{tmp_path}/a/test_1.jpg")
    
    def test_partial_dict_merge(self):
        test_cases = (
            ({"a": 1, "b": 2}, {"b": 3, "c": 4}, {"a": 1, "b": 2, "c": 4}),
            ({"a": 10, "b": {"a": 30}}, {"a": 20, "b": {"a": 5}}, {"a": 10, "b": {"a": 30}}),
            ({"a": {"b": 1}}, {"a": {"c": 2}}, {"a": {"b": 1, "c": 2}}),
            ({"a": {"b": 1}}, {}, {"a": {"b": 1}}),
            ({}, {"a": {"c": 2, "d": {"x": 1, "y": 2}}}, {"a": {"c": 2, "d": {"x": 1, "y": 2}}})
        )
        for d1, d2, expected in test_cases:
            assert utils.partial_dict_merge(d1, d2) == expected

    def test_load_env(self, tmp_path):
        os.makedirs(f"{tmp_path}/a/b", exist_ok=True)
        with open(f"{tmp_path}/.env", "w") as f:
            f.write("TEST_ENV=1")
        with open(f"{tmp_path}/a/.env", "w") as f:
            f.write("TEST_ENV=2")
        with open(f"{tmp_path}/a/b/.env", "w") as f:
            f.write("TEST_ENV=3")

        test_cases = [
            ([f"{tmp_path}/.env"], "1"),
            ([f"{tmp_path}/a/.env"], "2"),
            ([f"{tmp_path}/a/b/.env"], "3"),
            ([f"{tmp_path}/a/b/.env", f"{tmp_path}/a/.env"], "3"),
            ([f"{tmp_path}/a/.env", f"{tmp_path}/a/b/.env"], "2"),
            ([f"{tmp_path}/hi", f"{tmp_path}/.env"], "1"),
            ([f"{tmp_path}/a/hi"], None)
        ]
        for paths, expected in test_cases:
            os.environ.pop("TEST_ENV", None)
            utils.load_env(paths)
            assert os.environ.get("TEST_ENV", None) == expected

    def test_secure_path(self):
        test_cases = [
            ("image.jpg", "image.jpg"),
            ("../image.jpg", "/image.jpg"),
            ("./image.jpg", "/image.jpg"),
            ("image/../test.png", "image//test.png"),
            ("/a/b/", "/a/b/"),
            ("/a/b./!test.123.jpg.", "/a/b/test.123.jpg")
        ]
        for image_name, expected in test_cases:
            assert utils.secure_path(image_name) == expected