from pytest import raises

from app.config import config


class TestConfig:
    def test_load_and_access_config(self):
        c = {"paths": {"base_dir": "base/test"}, "list": ["1", "2"], "set": {"1"}, "num": 10, "bool": True}
        # Loading config changes all values to strings
        expected = {"paths": {"base_dir": "base/test"}, "list": "['1', '2']", "set": "{'1'}", "num": '10', "bool": 'True'}
        config.load_config(c)
        assert dict(config.config()) == expected

    def test_override_config(self): 
        c1 = {"paths": {"base_dir": "base/test"}} 
        c2 = {"paths": {"base_dir": "base/override"}} 
        config.load_config(c1)
        config.load_config(c2)
        assert config.config()["paths"]["base_dir"].as_str() == "base/override"

    def test_to_str(self):
        c = {"paths": {"base_dir": "base/test"}}
        config.load_config(c)
        cfg = config.config()
        assert cfg["paths"]["base_dir"].as_str() == "base/test"
        with raises(NotImplementedError):
            cfg["paths"].as_str()

    def test_to_int(self):
        c = {"test": {"count": 10}}
        config.load_config(c)
        cfg = config.config()
        assert cfg["test"]["count"].as_int() == 10
        with raises(NotImplementedError):
            cfg["test"].as_int()

    def test_to_bool(self):
        c = {"test": {"enabled": True}}
        config.load_config(c)
        cfg = config.config()
        assert cfg["test"]["enabled"].as_bool() is True
        with raises(NotImplementedError):
            cfg["test"].as_bool()

    def test_to_set(self):
        c = {"test": {"items": {"1", "2", "3"}}}
        config.load_config(c)
        cfg = config.config()
        assert cfg["test"]["items"].as_set().as_strs() == {"1", "2", "3"}
        assert cfg["test"]["items"].as_set().as_ints() == {1, 2, 3}
        assert cfg["test"]["items"].as_set().as_bools() == {True, True, True}
        with raises(NotImplementedError):
            cfg["test"].as_set()

    def test_to_list(self):
        c = {"test": {"items": ["1", "2", "3"]}}
        config.load_config(c)
        cfg = config.config()
        assert cfg["test"]["items"].as_list().as_strs() == ["1", "2", "3"]
        assert cfg["test"]["items"].as_list().as_ints() == [1, 2, 3]
        assert cfg["test"]["items"].as_list().as_bools() == [True, True, True]
        with raises(NotImplementedError):
            cfg["test"].as_list()
