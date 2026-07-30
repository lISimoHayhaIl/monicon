"""
Main application controller.

Orchestrates monitor communication, configuration, GUI, and keyboard shortcuts.
Follows the Dependency Injection pattern for loose coupling.
"""

import logging
import sys
from typing import Optional

from msi_monitor.core.monitor import IMonitor
from msi_monitor.config import ConfigManager
from msi_monitor.shortcuts import ShortcutManager, Shortcut
from msi_monitor.gui import TrayIcon

logger = logging.getLogger(__name__)


class MonitorController:
    """
    Main application controller.
    
    Manages:
    - Monitor connection and commands
    - Configuration persistence
    - Keyboard shortcut capture
    - System tray GUI
    
    Follows Single Responsibility Principle: only orchestrates interactions.
    """

    def __init__(self, monitor: IMonitor):
        """
        Initialize the application.
        
        Args:
            monitor: The IMonitor implementation to use
        """
        self.monitor = monitor
        self.config = ConfigManager()
        self.shortcuts = ShortcutManager()
        self.gui = TrayIcon()
        self._running = False

    def startup(self) -> None:
        """Start the application and all subsystems."""
        logger.info("Starting Monicon")

        try:
            # Connect to monitor
            self._connect_monitor()

            # Setup keyboard shortcuts
            self._setup_shortcuts()

            # Initialize GUI
            # self._setup_gui()

            # Start listening for shortcuts
            self.shortcuts.start()

            self._running = True
            logger.info("Monicon started successfully")

        except Exception as e:
            logger.error("Failed to start application: %s", e)
            self.shutdown()
            raise

    def shutdown(self) -> None:
        """Stop all subsystems gracefully."""
        logger.info("Shutting down Monicon")

        # Stop listening for shortcuts
        self.shortcuts.stop()

        # Close monitor connection
        if self.monitor.is_open:
            self.monitor.close()

        self._running = False
        logger.info("Monicon shut down")

    def _connect_monitor(self) -> None:
        """Connect to the configured monitor."""
        try:
            self.monitor.open()
            logger.info("Connected to monitor: %s", self.monitor.info.model_name)
        except Exception as e:
            logger.error("Failed to connect to monitor: %s", e)
            raise

    def _setup_shortcuts(self) -> None:
        """Register default keyboard shortcuts."""
        # Get shortcuts from config, with sensible defaults
        config = self.config.get()

        # Switch to DisplayPort (Ctrl+Super+1)
        shortcut_dp = config.shortcuts.get("switch_dp", Shortcut(["ctrl", "super"], "1"))
        self.shortcuts.register(shortcut_dp, lambda: self.switch_input("dp"))

        # Switch to HDMI1 (Ctrl+Super+2)
        shortcut_hdmi1 = config.shortcuts.get("switch_hdmi1", Shortcut(["ctrl", "super"], "2"))
        self.shortcuts.register(shortcut_hdmi1, lambda: self.switch_input("hdmi1"))

        # Cycle profile (Ctrl+Super+p)
        shortcut_profile = config.shortcuts.get("cycle_profile", Shortcut(["ctrl", "super"], "p"))
        self.shortcuts.register(shortcut_profile, lambda: self.cycle_profile())

        logger.debug("Shortcuts configured")

    def switch_input(self, source_id: str) -> None:
        """Switch monitor input source."""
        try:
            if self.monitor.set_input(source_id):
                logger.info("Switched input to: %s", source_id)
                # Update config
                source_name = next(
                    (s.display_name for s in self.monitor.info.inputs if s.id == source_id),
                    source_id
                )
                self.config.set_input(source_id, source_name)
            else:
                logger.warning("Failed to switch input")
        except Exception as e:
            logger.error("Error switching input: %s", e)

    def cycle_profile(self) -> None:
        """Cycle to next profile."""
        try:
            if self.monitor.next_profile():
                logger.info("Cycled to next profile")
            else:
                logger.warning("Failed to cycle profile")
        except Exception as e:
            logger.error("Error cycling profile: %s", e)

    def set_custom_input_name(self, input_id: str, name: str) -> None:
        """Allow user to customize input source display names."""
        self.config.set_custom_input_name(input_id, name)
        logger.info("Custom input name set: %s -> %s", input_id, name)

    def set_custom_profile_name(self, profile_id: str, name: str) -> None:
        """Allow user to customize profile display names."""
        self.config.set_custom_profile_name(profile_id, name)
        logger.info("Custom profile name set: %s -> %s", profile_id, name)

    def set_shortcut(self, action: str, modifiers: list, key: str) -> None:
        """Update a keyboard shortcut."""
        self.config.set_shortcut(action, modifiers, key)
        logger.info("Shortcut updated: %s -> %s", action, key)

    @property
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running

    def run(self) -> int:
        """Run the application main loop."""
        try:
            self.startup()
            # For now, run briefly then exit (will be replaced with GUI loop)
            import time
            while self._running:
                time.sleep(1)
            return 0
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error("Application error: %s", e)
            return 1
        finally:
            self.shutdown()
