import pytest
from datetime import datetime, timezone, timedelta
import time
import os
import shutil
from pathlib import Path
import json


from app.config import config
from app.utils import offline

class TestOffline:
    def test_write_poll_time(self, tmp_path: Path):
        c = {"paths": {"last_poll_file": tmp_path / "last_poll.txt"}}
        config.load_config(c)
        # 1. Test when file doesn't exist.
        # 2. Test overriding file.
        for _ in range(2):
            offline.write_poll_time()
            with open(config.config()['paths']['last_poll_file'].as_str(), 'r') as f:
                timestamp = f.readline().strip()
            poll_time = datetime.fromisoformat(timestamp)
            assert self.approx_curr_time(poll_time)
            time.sleep(0.15)

    def test_get_last_poll_file_doesnt_exist(self, tmp_path: Path):
        c = {"paths": {"last_poll_file": tmp_path / "last_poll.txt"}}
        config.load_config(c)
        assert not os.path.exists(config.config()['paths']['last_poll_file'].as_str())
        assert offline.get_last_poll() == datetime.fromtimestamp(0, timezone.utc)

    def test_get_last_poll_file_exists(self, tmp_path: Path):
        c = {"paths": {"last_poll_file": tmp_path / "last_poll.txt"}}
        config.load_config(c)
        offline.write_poll_time()
        assert os.path.exists(config.config()['paths']['last_poll_file'].as_str())
        poll_time = offline.get_last_poll()
        assert self.approx_curr_time(poll_time)

    def test_is_within_retention_period(self, tmp_path: Path):
        c = {
                "paths": {"last_poll_file": tmp_path / "last_poll.txt"},
                "queue": {"retention_days": 3},
        }
        config.load_config(c)
        last_poll_time = str(datetime.now(timezone.utc))
        with open(config.config()['paths']['last_poll_file'].as_str(), 'w') as f:
            f.write(last_poll_time + "\n")
        assert offline.is_within_retention_period()

    def test_is_not_within_retention_period(self, tmp_path: Path):
        c = {
                "paths": {"last_poll_file": tmp_path / "last_poll.txt"},
                "queue": {"retention_days": 3},
        }
        config.load_config(c)
        last_poll_time = str(datetime.now(timezone.utc) - timedelta(days=4))
        with open(config.config()['paths']['last_poll_file'].as_str(), 'w') as f:
            f.write(last_poll_time + "\n")
        assert not offline.is_within_retention_period()

    def test_save_simple_fs_snapshot(self, tmp_path: Path):
        c = {
            "files": {"allowed_prefixes": {"Shared"}},
            "paths": {
                "base_dir": tmp_path / "albums",
                "last_poll_file": tmp_path / "last_poll.txt"
            }
        }
        config.load_config(c)

        test_img = Path(__file__).parent.parent / "images" / "rotate_90_cw.jpg"
        base_dir = config.config()['paths']['base_dir'].as_str()
        snapshot_file = str(tmp_path / "snapshot.txt")

        imgs_in_snapshot = {f"Shared/1.jpg", f"Shared/2.jpg", f"Shared/a/1.jpg", f"Shared/a/2.jpg"}
        imgs_not_in_snapshot = {f"1.jpg", f"2.jpg"}

        os.makedirs(f"{base_dir}/albums/Shared/a", exist_ok=True)
        for img in imgs_in_snapshot.union(imgs_not_in_snapshot):
            shutil.copy(test_img, f"{base_dir}/albums/{img}")
        offline.write_poll_time()
        offline.save_simple_fs_snapshot(snapshot_file)

        with open(snapshot_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 2

        snapshot_timestamp = datetime.fromisoformat(lines[0].strip())
        assert self.approx_curr_time(snapshot_timestamp)

        file_list = json.loads(lines[1].strip())
        assert len(file_list) == len(imgs_in_snapshot)
        for f in file_list:
            f = f.replace("albums/", "")
            assert f in imgs_in_snapshot
            assert f not in imgs_not_in_snapshot


    def test_create_offline_event(self):
        test_cases = [
            ("CREATE", "/path/to/file.jpg", "", "CREATE,/path/to/file.jpg"),
            ("DELETE", "/path/to/file.jpg", "", "DELETE,/path/to/file.jpg"),
            ("MOVE", "/path/from/file.jpg", "/new/path/to/file.jpg", "MOVE,/path/from/file.jpg,/new/path/to/file.jpg"),
        ]
        for t in test_cases:
            evt = offline.create_offline_event(*t[:3])
            timestamp, rest = evt.split(',', 1)
            assert rest == t[3]
            assert self.approx_curr_time(datetime.fromisoformat(timestamp))

    def test_save_offline_events(self, tmp_path: Path):
        events = [
            offline.create_offline_event("CREATE", "/path/to/file1.jpg"),
            offline.create_offline_event("DELETE", "/path/to/file2.jpg"),
            offline.create_offline_event("MOVE", "/path/from/file3.jpg", "/new/path/to/file3.jpg"),
        ]
        offline.save_offline_events(str(tmp_path / "offline_events.json"), events)
        with open(tmp_path / "offline_events.json", "r") as f:
            lines = f.readlines()
        assert len(lines) == len(events)
        for line, event in zip(lines, events):
            assert line.strip() == event

    def test_get_offline_events(self, tmp_path: Path):
        events = [
            {"timestamp": datetime.now(timezone.utc), "event": "CREATE", "path": "/path/to/file1.jpg"},
            {"timestamp": datetime.now(timezone.utc), "event": "CREATE", "path": "/path/to/file1.jpg"},
            {"timestamp": datetime.now(timezone.utc), "event": "DELETE", "path": "/path/to/file2.jpg"},
            {"timestamp": datetime.now(timezone.utc), "event": "MOVE", "path": "/path/from/file3.jpg", "new_path": "/new/path/to/file3.jpg"},
        ]
        evt_strs = [offline.create_offline_event(evt["event"], evt["path"], evt.get("new_path", "")) for evt in events]
        events_file = str(tmp_path / "offline_events.json")
        offline.save_offline_events(events_file, evt_strs)
        parsed_events = offline.get_offline_events(events_file)
        for e, pe in zip(events, parsed_events):
            assert e["event"] == pe["event"]
            assert e["path"] == pe["path"]
            assert e.get("new_path", "") == pe.get("newPath", "")
            assert self.times_approx_equal(datetime.fromisoformat(pe["timestamp"]), e["timestamp"])

    def test_clear_offline_events(self, tmp_path: Path):
        events_file = tmp_path / "offline_events.json"
        events_file.write_text("TEST")
        offline.clear_offline_events(str(events_file))
        evts = offline.get_offline_events(str(events_file))
        assert evts == []

    def test_get_snapshot_time_file_not_found(self):
        c = {
            "paths": {"fs_snapshot_file": "non_existent_file.txt"}
        }
        config.load_config(c)
        assert offline.get_snapshot_time() is None

    def test_get_snapshot_time(self, tmp_path: Path):
        c = {
            "files": {"allowed_prefixes": {"Shared"}},
            "paths": {
                "base_dir": tmp_path / "albums",
                "last_poll_file": tmp_path / "last_poll.txt",
                "fs_snapshot_file": str(tmp_path / "snapshot.json")
            }
        }
        config.load_config(c)

        test_img = Path(__file__).parent.parent / "images" / "rotate_90_cw.jpg"
        base_dir = config.config()['paths']['base_dir'].as_str()
        snapshot_file = config.config()['paths']['fs_snapshot_file'].as_str()

        imgs = {f"Shared/1.jpg", f"Shared/2.jpg"}
        os.makedirs(f"{base_dir}/albums/Shared", exist_ok=True)

        for img in imgs:
            shutil.copy(test_img, f"{base_dir}/albums/{img}")
        offline.write_poll_time()
        offline.save_simple_fs_snapshot(snapshot_file)

        timestamp = offline.get_snapshot_time()
        assert timestamp is not None
        assert self.approx_curr_time(timestamp)

    def approx_curr_time(self, timestamp: datetime, rel=0.1):
        now = datetime.now(timezone.utc)
        return self.times_approx_equal(timestamp, now, rel)

    def times_approx_equal(self, t1: datetime, t2: datetime, rel=0.1):
        return pytest.approx(t1.timestamp(), rel) == t2.timestamp()