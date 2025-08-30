import ast
import os
from typing import Union

_config = None

class Config:
    def __getitem__(self, key: str) -> Union['ConfigDict', 'ConfigValue']:
        raise NotImplementedError()

    def as_int(self) -> int:
        raise NotImplementedError()

    def as_str(self) -> str:
        raise NotImplementedError()

    def as_bool(self) -> bool:
        raise NotImplementedError()

    def as_list(self) -> 'ConfigListValue':
        raise NotImplementedError()

    def as_set(self) -> 'ConfigSetValue':
        raise NotImplementedError()

class ConfigDict(Config):
    def __init__(self, config: dict):
        self.config: dict[str, Union['ConfigDict', 'ConfigValue']] = {
            k: ConfigDict(v) if isinstance(v, dict) else ConfigValue(v)
            for k, v in config.items()
        }

    def __getitem__(self, key):
        return self.config[key]

    def __repr__(self):
        return str(self.config)
    
    def __iter__(self):
        return (
            (k, dict(v) if isinstance(v, ConfigDict) else v.val)
            for k, v in self.config.items()
        )

class ConfigValue(Config):
    def __init__(self, val):
        self.val = str(val)

    def as_str(self):
        return self.val

    def as_int(self):
        return int(self.val)

    def as_bool(self):
        return bool(self.val)

    def as_list(self):
        data = ast.literal_eval(self.val)
        if not isinstance(data, list):
            raise ValueError("Config value is not a list")
        return ConfigListValue(data)

    def as_set(self):
        data = ast.literal_eval(self.val)
        if not isinstance(data, set):
            raise ValueError("Config value is not a set")
        return ConfigSetValue(data)

    def __repr__(self):
        return self.val
    
    
    
class ConfigSetValue(Config):
    def __init__(self, values: set):
        self.values = values

    def as_strs(self):
        return {str(v) for v in self.values}

    def as_ints(self):
        return {int(v) for v in self.values}

    def as_bools(self):
        return {bool(v) for v in self.values}

class ConfigListValue:
    def __init__(self, values: list):
        self.values = values

    def as_strs(self):
        return [str(v) for v in self.values]

    def as_ints(self):
        return [int(v) for v in self.values]

    def as_bools(self):
        return [bool(v) for v in self.values]

def default_config():
    config_dir = os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album'))
    base_dir = os.path.abspath(os.path.expandvars(os.getenv('PHOTO_STORAGE_PATH', '$HOME/pi-photo-album')))

    config = {
        "default_settings": {
            "album": "Shared",
            "isEnabled": False,
            "blend": 250,
            "speed": 30,
            "randomize": False
        },
        "paths": {
            "config_dir": config_dir,
            "settings_file": f"{config_dir}/settings.json",
            "env_file": f"{config_dir}/.env",
            "last_poll_file": f"{config_dir}/last_poll.txt",
            "fs_snapshot_file": f"{config_dir}/fs_snapshot.json",
            "offline_events_file": f"{config_dir}/events.csv",
            "active_slideshow_file": f"{config_dir}/active_slideshow.txt",
            "base_dir": base_dir,
            "tmp_storage_dir": f"{base_dir}/tmp"
        },
        "files": {
            "max_content_length": 512 * 1024 * 1024,  # 512MB
            "allowed_file_extensions": {'jpg', 'jpeg', 'png', 'webp', 'heif', 'heic'},
            "allowed_prefixes": {'Shared', os.getenv('USERNAME')} if os.getenv('USERNAME') else {'Shared'}
        },
        "queue": {
            "retention_days": 4
        },
        "url": {
            "api_url": f"http://localhost:{os.getenv('API_PORT', 5555)}",
            "sqs_ping_url": f"https://sqs.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/ping",
            "s3_ping_url": f"https://s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/ping"
        }
    }

    return config

def load_config(config: dict = default_config()):
    global _config
    _config = ConfigDict(config)

def config():
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return _config