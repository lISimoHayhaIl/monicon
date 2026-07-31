"""
Unit tests for Monicon core components.

Run with: pytest tests/
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from msi_monitor.config import ConfigManager, ApplicationConfig, ShortcutConfig
from msi_monitor.shortcuts import Shortcut, ShortcutManager
from msi_monitor.core.registry import MonitorRegistry
from msi_monitor.core.monitor import InputSource, Profile, MonitorInfo


# ============================================================================
#  Configuration Tests
# ============================================================================

class TestApplicationConfig:
    """Test ApplicationConfig dataclass."""

    def test_create_default_config(self):
        """Test creating config with defaults."""
        config = ApplicationConfig()
        # monitor_model stores the MonitorRegistry id (see msi_monitor/monitors/*.json),
        # not the human-readable model name — that keeps config.json stable even if a
        # monitor's display name is edited later.
        assert config.monitor_model == "msi_mpg_341cqr"
        assert config.minimize_to_tray is True
        assert config.confirm_on_quit is True

    def test_config_to_dict(self):
        """Test config serialization to dict."""
        config = ApplicationConfig(monitor_model="Test Monitor")
        data = config.to_dict()
        assert data['monitor_model'] == "Test Monitor"
        assert isinstance(data['shortcuts'], dict)

    def test_config_from_dict(self):
        """Test config deserialization from dict."""
        data = {
            'monitor_model': 'Custom Monitor',
            'selected_input_id': 'dp',
            'shortcuts': {},
            'input_names': {},
            'profile_names': {},
        }
        config = ApplicationConfig.from_dict(data)
        assert config.monitor_model == 'Custom Monitor'
        assert config.selected_input_id == 'dp'


class TestConfigManager:
    """Test ConfigManager persistence."""

    def test_create_config_dir(self):
        """Test that config directory is created."""
        cm = ConfigManager()
        assert cm.config_dir.exists()
        assert cm.config_dir.name == "monicon"

    def test_set_and_get_input(self):
        """Test setting and retrieving input configuration."""
        cm = ConfigManager()
        cm.set_input("dp", "DisplayPort")
        config = cm.get()
        assert config.selected_input_id == "dp"
        assert config.selected_input_name == "DisplayPort"

    def test_custom_input_names(self):
        """Test custom input name management."""
        cm = ConfigManager()
        cm.set_custom_input_name("dp", "My Display")
        assert cm.get_custom_input_name("dp", "default") == "My Display"
        assert cm.get_custom_input_name("unknown", "default") == "default"


# ============================================================================
#  Shortcut Tests
# ============================================================================

class TestShortcut:
    """Test Shortcut representation."""

    def test_create_shortcut(self):
        """Test creating a shortcut."""
        shortcut = Shortcut(["ctrl", "shift"], "d")
        assert "ctrl" in shortcut.modifiers
        assert "shift" in shortcut.modifiers
        assert shortcut.key == "d"

    def test_shortcut_equality(self):
        """Test shortcut equality comparison."""
        s1 = Shortcut(["ctrl", "shift"], "d")
        s2 = Shortcut(["shift", "ctrl"], "d")
        assert s1 == s2  # Order shouldn't matter

    def test_shortcut_repr(self):
        """Test shortcut string representation."""
        shortcut = Shortcut(["ctrl", "shift"], "d")
        repr_str = repr(shortcut)
        assert "ctrl" in repr_str
        assert "d" in repr_str


class TestShortcutManager:
    """Test ShortcutManager."""

    def test_register_shortcut(self):
        """Test registering a keyboard shortcut."""
        manager = ShortcutManager()
        shortcut = Shortcut(["ctrl"], "d")
        callback = Mock()
        manager.register(shortcut, callback)
        assert shortcut in manager._shortcuts

    def test_unregister_shortcut(self):
        """Test unregistering a shortcut."""
        manager = ShortcutManager()
        shortcut = Shortcut(["ctrl"], "d")
        callback = Mock()
        manager.register(shortcut, callback)
        manager.unregister(shortcut, callback)
        assert callback not in manager._shortcuts.get(shortcut, [])

    def test_start_stop_listener(self):
        """Test starting and stopping the listener."""
        manager = ShortcutManager()
        manager.start()
        assert manager.is_running is True
        manager.stop()
        assert manager.is_running is False


# ============================================================================
#  Monitor Registry Tests
# ============================================================================

class TestMonitorRegistry:
    """Test MonitorRegistry."""

    def test_builtin_monitors_loaded(self):
        """Test that built-in monitors are loaded."""
        registry = MonitorRegistry()
        monitors = registry.list_ids()
        assert 'msi_mpg_341cqr' in monitors

    def test_get_monitor_by_id(self):
        """Test retrieving monitor by ID."""
        registry = MonitorRegistry()
        monitor = registry.get('msi_mpg_341cqr')
        assert monitor is not None
        assert monitor.model_name == "MSI MPG 341CQR QD-OLED X36"

    def test_get_monitor_by_usb_id(self):
        """Test finding monitor by USB IDs."""
        registry = MonitorRegistry()
        monitor = registry.get_by_usb_id(0x1462, 0x3fa4)
        assert monitor is not None
        assert monitor.vendor_id == 0x1462

    def test_list_all_monitors(self):
        """Test listing all available monitors."""
        registry = MonitorRegistry()
        monitors = registry.list_all()
        assert len(monitors) > 0
        assert all(isinstance(m, MonitorInfo) for m in monitors)


# ============================================================================
#  Monitor Info Tests
# ============================================================================

class TestMonitorInfo:
    """Test MonitorInfo structures."""

    def test_create_monitor_info(self):
        """Test creating monitor information."""
        inputs = [InputSource("dp", "DisplayPort")]
        profiles = [Profile("eco", "Eco")]
        info = MonitorInfo(
            model_name="Test Monitor",
            vendor_id=0x1234,
            product_id=0x5678,
            inputs=inputs,
            profiles=profiles,
        )
        assert info.model_name == "Test Monitor"
        assert len(info.inputs) == 1
        assert len(info.profiles) == 1

    def test_input_source(self):
        """Test InputSource data class."""
        inp = InputSource("dp", "DisplayPort", "Main display input")
        assert inp.id == "dp"
        assert inp.display_name == "DisplayPort"
        assert inp.description == "Main display input"

    def test_profile(self):
        """Test Profile data class."""
        prof = Profile("gaming", "Gaming", "Optimized for gaming")
        assert prof.id == "gaming"
        assert prof.display_name == "Gaming"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
