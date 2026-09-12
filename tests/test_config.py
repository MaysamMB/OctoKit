import json

from core.config import AppConfig, ConfigManager


def test_defaults_are_safe(tmp_path):
    manager = ConfigManager(config_path=tmp_path / "config.json")
    assert manager.config.confirm_destructive_actions is True
    assert manager.config.dry_run_by_default is True
    assert manager.config.default_min_age_minutes == 120


def test_creates_file_on_first_load(tmp_path):
    path = tmp_path / "config.json"
    assert not path.exists()
    ConfigManager(config_path=path)
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["theme"] == "system"


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json", encoding="utf-8")
    manager = ConfigManager(config_path=path)
    assert manager.config == AppConfig()


def test_unknown_keys_are_dropped_safely(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"theme": "dark", "totally_made_up_field": 123}), encoding="utf-8")
    manager = ConfigManager(config_path=path)
    assert manager.config.theme == "dark"
    assert not hasattr(manager.config, "totally_made_up_field")


def test_update_persists(tmp_path):
    path = tmp_path / "config.json"
    manager = ConfigManager(config_path=path)
    manager.update(theme="dark", default_min_age_minutes=60)

    reloaded = ConfigManager(config_path=path)
    assert reloaded.config.theme == "dark"
    assert reloaded.config.default_min_age_minutes == 60


def test_onboarding_dismissed_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    manager = ConfigManager(config_path=path)
    manager.set_onboarding_dismissed("inventory", True)

    reloaded = ConfigManager(config_path=path)
    assert reloaded.config.onboarding_dismissed.get("inventory") is True

    reloaded.reset_onboarding()
    assert reloaded.config.onboarding_dismissed == {}
