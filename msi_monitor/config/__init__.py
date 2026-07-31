"""
Configuration and settings management.

Handles persistent storage of user preferences, shortcuts, and monitor selections.
Follows the Single Responsibility Principle: only handles configuration I/O.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShortcutConfig:
    """Keyboard shortcut configuration."""
    action: str           # "switch_input", "cycle_profile", "show_window"
    modifiers: list       # ["ctrl", "shift", "alt", "super"]
    key: str              # "F1", "i", "p", etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortcutConfig":
        return cls(**data)


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    monitor_model: str = "msi_mpg_341cqr"  # Registry id (see msi_monitor/monitors/*.json), persists across restarts
    # NOTE: the MSI protocol has no reliable "query current input/profile" command
    # (the monitor echoes the same fixed response regardless of the active input —
    # confirmed by capture analysis), so we cannot know the monitor's real state on
    # first launch or if it was changed via the physical OSD/remote. Defaulting to
    # "Unknown" instead of guessing a specific input (e.g. "DisplayPort") avoids
    # showing the user information that may be flatly wrong. The values below are
    # only updated when the app itself successfully sends a switch command.
    selected_input_name: Optional[str] = None   # User-friendly name; None = unknown
    selected_input_id: Optional[str] = None     # Internal ID; None = unknown
    selected_profile_name: Optional[str] = None  # User-friendly name; None = unknown
    selected_profile_id: Optional[str] = None    # Internal ID; None = unknown
    autostart: bool = False
    minimize_to_tray: bool = True
    confirm_on_quit: bool = True
    theme: str = "auto"  # "auto", "light", "dark"
    
    # Shortcuts: action -> ShortcutConfig
    shortcuts: Dict[str, ShortcutConfig] = field(default_factory=dict)

    # Custom input/profile names: id -> custom display name
    input_names: Dict[str, str] = field(default_factory=dict)
    profile_names: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to JSON-serializable dict."""
        d = asdict(self)
        d['shortcuts'] = {k: v.to_dict() for k, v in self.shortcuts.items()}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationConfig":
        """Create config from dict."""
        shortcuts = {}
        if 'shortcuts' in data:
            for action, cfg in data['shortcuts'].items():
                shortcuts[action] = ShortcutConfig.from_dict(cfg)
        data['shortcuts'] = shortcuts
        return cls(**data)


class ConfigManager:
    """
    Manages persistent application configuration.

    Configuration is stored in XDG config directory (Linux standard).
    $XDG_CONFIG_HOME/monicon/config.json (defaults to ~/.config/monicon/config.json)
    """

    def __init__(self, app_name: str = "monicon"):
        """Initialize config manager."""
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self._config = ApplicationConfig()
        self._load()

    @staticmethod
    def _get_config_dir() -> Path:
        """Get XDG config directory, create if needed."""
        xdg_config = Path.home() / ".config" / "monicon"
        xdg_config.mkdir(parents=True, exist_ok=True)
        return xdg_config

    def _load(self) -> None:
        """Load config from file, use defaults if not found."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self._config = ApplicationConfig.from_dict(data)
                    logger.info("Loaded config from %s", self.config_file)
            except Exception as e:
                logger.warning("Failed to load config: %s. Using defaults.", e)
                self._config = ApplicationConfig()
        else:
            logger.debug("No config file found. Using defaults.")
            self._config = ApplicationConfig()

    def save(self) -> None:
        """Save current config to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.info("Saved config to %s", self.config_file)
        except Exception as e:
            logger.error("Failed to save config: %s", e)

    def get(self) -> ApplicationConfig:
        """Get current config object."""
        return self._config

    def set_monitor(self, model: str) -> None:
        """Set the selected monitor model."""
        self._config.monitor_model = model
        self.save()

    def set_input(self, input_id: str, display_name: str) -> None:
        """Set selected input."""
        self._config.selected_input_id = input_id
        self._config.selected_input_name = display_name
        self.save()

    def set_profile(self, profile_id: str, display_name: str) -> None:
        """Set selected profile."""
        self._config.selected_profile_id = profile_id
        self._config.selected_profile_name = display_name
        self.save()

    def set_shortcut(self, action: str, modifiers: list, key: str) -> None:
        """Set a keyboard shortcut."""
        self._config.shortcuts[action] = ShortcutConfig(action, modifiers, key)
        self.save()

    def get_shortcut(self, action: str) -> Optional[ShortcutConfig]:
        """Get shortcut config for an action."""
        return self._config.shortcuts.get(action)

    def set_custom_input_name(self, input_id: str, display_name: str) -> None:
        """Set custom display name for an input source."""
        self._config.input_names[input_id] = display_name
        self.save()

    def get_custom_input_name(self, input_id: str, default: str) -> str:
        """Get custom display name for input, with fallback to default."""
        return self._config.input_names.get(input_id, default)

    def set_custom_profile_name(self, profile_id: str, display_name: str) -> None:
        """Set custom display name for a profile."""
        self._config.profile_names[profile_id] = display_name
        self.save()

    def get_custom_profile_name(self, profile_id: str, default: str) -> str:
        """Get custom display name for profile, with fallback to default."""
        return self._config.profile_names.get(profile_id, default)
