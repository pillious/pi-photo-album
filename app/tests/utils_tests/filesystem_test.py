from pathlib import Path

from app.config import config
from app.utils import filesystem
from app.tests import utils

class TestFilesystem:
    def test_get_file_structure(self, tmp_path: Path):
        fs = {
            "albums": {
                "user1": {
                    "file.png": "",
                    "abc": {
                        "file2.png": "",
                        "file3.png": "",
                    },
                    "file2.png": ""
                },
                "Shared": {
                    "file.png": "",
                    "empty": {}
                }
            }
        }

        utils.create_fs(tmp_path, fs)
        assert filesystem.get_file_structure(str(tmp_path / "albums")) == fs

    def test_is_file_owner(self):
        c = {"files": {"allowed_prefixes": {"user1", "Shared"}}}
        config.load_config(c)

        test_cases = [
            ("user1/file.txt", True),
            ("Shared/abc/file.txt", True),
            ("albums/user1/file.txt", True),
            ("user2/Shared/user1/file.txt", False),
            ("file.txt", False),
            ("albums/abc/Shared/file.txt", False)
        ]

        for file_path, expected in test_cases:
            assert filesystem.is_file_owner(file_path) == expected

    def test_list_files_in_dir(self, tmp_path: Path):
        allowed_prefixes = ["user1/a", "Shared"]
        fs = {
            "albums": {
                "user1": {
                    "file.png": "",
                    "a": {
                        "file2.png": "",
                        "file3.png": "",
                    },
                    "b": {
                        "file2.png": ""
                    }
                },
                "Shared": {
                    "file.png": "",
                    "c": {
                        "file4.png": ""
                    }
                }
            }
        }
        utils.create_fs(tmp_path, fs)

        expected = [
            "user1/a/file2.png",
            "user1/a/file3.png",
            "Shared/file.png",
            "Shared/c/file4.png"
        ]
        files = filesystem.list_files_in_dir(str(tmp_path / "albums"), allowed_prefixes)
        assert len(files) == len(expected)
        assert all(f in expected for f in files)

    def test_key_to_abs_path(self):
        c = {"paths": {"base_dir": "base"}}
        config.load_config(c)
        assert filesystem.key_to_abs_path("file.txt") == config.config()["paths"]["base_dir"].as_str() + "/file.txt"

    def test_strip_base_dir(self):
        c = {"paths": {"base_dir": "base/a/b"}}
        config.load_config(c)

        test_cases = [
            ("base/a/b/file.txt", "file.txt"),
            ("base/a/b/c/d/file.txt", "c/d/file.txt"),
            ("a/b/file.txt", "a/b/file.txt"),
            ("file.txt", "file.txt")
        ]

        for input_path, expected_output in test_cases:
            assert filesystem.strip_base_dir(input_path) == expected_output

    def test_remove_albums_prefix(self):
        test_cases = [
            ("albums/user1/file.txt", "user1/file.txt"),
            ("albums/file.txt", "file.txt"),
            ("a/albums/c/file.txt", "a/albums/c/file.txt"),
            ("file.txt", "file.txt")
        ]

        for input_path, expected_output in test_cases:
            assert filesystem.remove_albums_prefix(input_path) == expected_output

    def test_remove_dirs(self, tmp_path: Path):
        fs = {
            "albums": {
                "user1": {
                    "file.txt": "",
                    "a": {
                        "file3.txt": "",
                        "c": {},
                    },
                },
                "Shared": {},
                "Test": {"a": {"b": {"c": {}}}}
            }
        }

        test_cases = [
            ("Test", {"albums": {"Test": {"a": {"b": {"c": {}}}}}}, {"albums": {"Test": {"a": {"b": {"c": {}}}}}}),
            ("Test/a/b/c", {"albums": {"Test": {"a": {"b": {"c": {}}}}}}, {"albums": {"Test": {}}}),
            ("Shared", {"albums": {"Shared": {}, "user1": {}}}, {"albums": {"Shared": {}, "user1": {}}}),
            ("user1/a/c", {
                "albums": {
                    "user1": {
                        "file.txt": "",
                        "a": {
                            "file3.txt": "",
                            "c": {},
                        },
                    },
                }
            }, {
                "albums": {
                    "user1": {
                        "file.txt": "",
                        "a": {
                            "file3.txt": "",
                        },
                    },
                }
            })
        ]

        for i, (path, fs, expected_fs) in enumerate(test_cases):
            base_dir = tmp_path / str(i)
            utils.create_fs(base_dir, fs)
            filesystem.remove_dirs(str(base_dir / "albums"), path)
            assert filesystem.get_file_structure(str(base_dir))[str(i)]== expected_fs


