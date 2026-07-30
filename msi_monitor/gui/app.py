"""
Monicon main application - system tray GUI with keybindings.

Integrates:
- Monitor communication (MSIMPEG341CQR)
- Configuration management
- Global keyboard shortcuts
- PyQt6 system tray GUI
"""

import logging
import sys
from typing import Optional

from msi_monitor.core import HIDDeviceError
from msi_monitor.core.monitor import IMonitor
from msi_monitor.core.registry import MonitorRegistry
from msi_monitor.monitors import MSIMPEG341CQR
from msi_monitor.config import ConfigManager
from msi_monitor.shortcuts import ShortcutManager, Shortcut
from msi_monitor.gui.window import MoniconicoTrayWindow

logger = logging.getLogger(__name__)


class MonitorApplicationGUI:
    """
    Complete Monicon application with GUI and keyboard shortcuts.
    
    Responsibilities:
    - Initialize monitor connection
    - Load configuration
    - Start keyboard shortcut listener
    - Show system tray with settings and menus
    """

    def __init__(self):
        """Initialize the application."""
        self.config = ConfigManager()
        self.monitor: Optional[IMonitor] = None
        self.shortcuts = ShortcutManager()
        self.gui = MoniconicoTrayWindow()
        self._running = False

    def startup(self) -> None:
        """Start the application."""
        logger.info("Starting Monicon GUI")

        try:
            # Detect and connect to monitor
            self._connect_monitor()

            # Prepare input/profile display names
            inputs = self._get_input_display_names()
            profiles = self._get_profile_display_names()

            # Initialize GUI
            self.gui.initialize(
                inputs=inputs,
                profiles=profiles,
                current_input=self.config.get().selected_input_id,
                current_profile=self.config.get().selected_profile_id,
            )

            # Register callbacks
            self.gui.set_on_input_changed(self._on_input_changed)
            self.gui.set_on_profile_changed(self._on_profile_changed)
            self.gui.set_on_quit_requested(self._on_quit_requested)

            # Setup keyboard shortcuts
            self._setup_shortcuts()

            # Start shortcut listener
            self.shortcuts.start()

            self._running = True
            logger.info("Monicon GUI started successfully")

        except Exception as e:
            logger.error("Failed to start application: %s", e)
            self.shutdown()
            raise

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down Monicon")

        self.shortcuts.stop()

        if self.monitor and self.monitor.is_open:
            try:
                self.monitor.close()
            except Exception as e:
                logger.warning("Error closing monitor: %s", e)

        self._running = False

    def _connect_monitor(self) -> None:
        """Detect and connect to the monitor."""
        logger.debug("Detecting monitor...")

        # Create monitor instance (hardcoded to MPG 341CQR for now)
        # TODO: Use registry to auto-detect
        self.monitor = MSIMPEG341CQR()

        try:
            self.monitor.open()
            logger.info("Connected to: %s", self.monitor.info.model_name)
        except HIDDeviceError as e:
            logger.error("Monitor not found: %s", e)
            logger.info("Continuing in offline mode (GUI only)")
            self.monitor = None

    def _get_input_display_names(self) -> dict:
        """Get display names for input sources (with custom names applied)."""
        if not self.monitor:
            return {}

        result = {}
        for inp in self.monitor.info.inputs:
            custom_name = self.config.get_custom_input_name(inp.id, inp.display_name)
            result[inp.id] = custom_name
        return result

    def _get_profile_display_names(self) -> dict:
        """Get display names for profiles (with custom names applied)."""
        if not self.monitor:
            return {}

        result = {}
        for prof in self.monitor.info.profiles:
            custom_name = self.config.get_custom_profile_name(prof.id, prof.display_name)
            result[prof.id] = custom_name
        return result

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        config = self.config.get()

        # Default shortcuts (can be overridden in config)
        shortcuts_config = {
            "switch_dp": {"modifiers": ["ctrl", "super"], "key": "1"},
            "switch_hdmi1": {"modifiers": ["ctrl", "super"], "key": "2"},
            "cycle_profile": {"modifiers": ["ctrl", "super"], "key": "p"},
        }

        # Override with config if present
        if config.shortcuts:
            for action, shortcut_cfg in config.shortcuts.items():
                shortcuts_config[action] = {
                    "modifiers": shortcut_cfg.modifiers,
                    "key": shortcut_cfg.key,
                }

        # Register shortcuts
        try:
            for action, cfg in shortcuts_config.items():
                shortcut = Shortcut(cfg["modifiers"], cfg["key"])

                if action == "switch_dp":
                    self.shortcuts.register(shortcut, lambda: self._switch_input("dp"))
                elif action == "switch_hdmi1":
                    self.shortcuts.register(shortcut, lambda: self._switch_input("hdmi1"))
                elif action == "cycle_profile":
                    self.shortcuts.register(shortcut, self._cycle_profile)

                logger.debug("Registered shortcut: %s -> %s", action, shortcut)

        except Exception as e:
            logger.error("Failed to setup shortcuts: %s", e)

    def _switch_input(self, source_id: str) -> None:
        """Switch monitor input source."""
        if not self.monitor:
            logger.warning("Monitor not connected")
            return

        try:
            if self.monitor.set_input(source_id):
                self.config.set_input(source_id, self._get_input_display_names().get(source_id, source_id))
                logger.info("Switched input to: %s", source_id)
            else:
                logger.warning("Failed to switch input")
        except Exception as e:
            logger.error("Error switching input: %s", e)

    def _cycle_profile(self) -> None:
        """Cycle to next profile."""
        if not self.monitor:
            logger.warning("Monitor not connected")
            return

        try:
            if self.monitor.next_profile():
                logger.info("Cycled to next profile")
            else:
                logger.warning("Failed to cycle profile")
        except Exception as e:
            logger.error("Error cycling profile: %s", e)

    def _on_input_changed(self, input_id: str) -> None:
        """Callback when user selects input from tray menu."""
        logger.debug("User selected input: %s", input_id)
        self._switch_input(input_id)

    def _on_profile_changed(self, profile_id: str) -> None:
        """Callback when user selects profile from tray menu."""
        logger.debug("User selected profile: %s", profile_id)
        if not self.monitor:
            logger.warning("Monitor not connected")
            return

        # TODO: Implement profile selection (currently only cycle available)
        logger.info("Profile selection via menu not yet implemented")

    def _on_quit_requested(self) -> None:
        """Callback when user requests quit."""
        logger.info("User requested quit")
        self.shutdown()

    def run(self) -> int:
        """Run the application."""
        try:
            self.startup()
            return self.gui.run()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error("Application error: %s", e)
            return 1
        finally:
            self.shutdown()

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
