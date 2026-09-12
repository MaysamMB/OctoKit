"""
Centralized, JSON-backed application configuration.

Design goals (see spec sections 22-23, 30):
- A single source of truth for settings; nothing hardcoded in individual
  widgets.
- Never crash on a missing or corrupt config file — fall back to defaults
  and log a warning instead.
- Every field has a safe, conservative default (e.g. destructive-action
  confirmation defaults to ON).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger
from core.paths import get_config_path, get_user_templates_dir

logger = get_logger("core.config")

CONFIG_VERSION = 1


@dataclass
class AppConfig:
    config_version: int = CONFIG_VERSION

    # General
    theme: str = "system"  # "light" | "dark" | "system"
    confirm_destructive_actions: bool = True
    start_maximized: bool = False

    # Project Generator
    default_project_location: str = ""  # "" => user is prompted each time
    template_directory: str = ""  # "" => use default user templates dir

    # Temp Files Cleaner
    default_min_age_minutes: int = 120
    dry_run_by_default: bool = True
    include_recycle_bin_by_default: bool = True

    # Leftovers Cleaner
    require_typed_confirmation_for_registry: bool = True

    # Logging
    log_level: str = "INFO"

    # Onboarding — per-feature "first use" intro dismissed flags
    onboarding_dismissed: dict[str, bool] = field(default_factory=dict)

    def resolved_template_directory(self) -> Path:
        if self.template_directory:
            return Path(self.template_directory)
        return get_user_templates_dir()


class ConfigManager:
    """Loads, validates, and persists AppConfig as JSON."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or get_config_path()
        self._config = self._load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def _load(self) -> AppConfig:
        if not self.config_path.exists():
            logger.info("No existing config found; creating defaults at %s", self.config_path)
            config = AppConfig()
            self._save(config)
            return config

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root is not an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "Config file at %s could not be read (%s). Using defaults; "
                "the file will be rewritten on next save.",
                self.config_path,
                exc,
            )
            return AppConfig()

        defaults = asdict(AppConfig())
        # Only accept known keys; unknown/legacy keys are dropped safely.
        merged = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}
        try:
            return AppConfig(**merged)
        except TypeError as exc:
            logger.warning("Config file had an incompatible shape (%s); using defaults.", exc)
            return AppConfig()

    def _save(self, config: AppConfig) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(asdict(config), indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("Could not save configuration to %s: %s", self.config_path, exc)

    def save(self) -> None:
        self._save(self._config)

    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if not hasattr(self._config, key):
                logger.warning("Ignoring unknown config key: %s", key)
                continue
            setattr(self._config, key, value)
        self.save()

    def set_onboarding_dismissed(self, feature_key: str, dismissed: bool = True) -> None:
        self._config.onboarding_dismissed[feature_key] = dismissed
        self.save()

    def reset_onboarding(self) -> None:
        self._config.onboarding_dismissed = {}
        self.save()
