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
from msi_monitor.monitors import create_monitor
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
        self.registry = MonitorRegistry()
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
                monitors=self._get_monitor_display_names(),
                current_monitor=self.config.get().monitor_model,
                shortcuts=self._get_shortcuts_dict(),
            )

            # Register callbacks
            self.gui.set_on_input_changed(self._on_input_changed)
            self.gui.set_on_profile_changed(self._on_profile_changed)
            self.gui.set_on_quit_requested(self._on_quit_requested)
            self.gui.set_on_settings_changed(self._on_settings_changed)
            self.gui.set_on_monitor_selected(self._on_monitor_selected)

            # Setup keyboard shortcuts
            self._setup_shortcuts()

            # Start shortcut listener
            self.shortcuts.start()

            # If the monitor could not be reached, tell the user visibly instead
            # of only logging it — previously this was silent, making input/profile
            # switches appear to "do nothing" with no indication why.
            if self.monitor is None:
                self.gui.show_error(
                    "Monitor not found",
                    "Monicon could not connect to a monitor and is running in "
                    "offline mode. Input/profile switching will have no effect "
                    "until a monitor is detected.\n\n"
                    "Check that: the monitor is powered on and connected via USB, "
                    "the correct monitor model is selected in the tray menu, and "
                    "your user has permission to access the HID device (see "
                    "90-msi-monitor.rules).",
                )

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
        """
        Detect and connect to the monitor selected in config.

        The monitor model is chosen via MonitorRegistry (req #12: monitor
        selection reads the monitors/ folders and persists until changed).
        If the persisted model has no protocol implementation yet, or the
        device is not physically present, the app still starts in offline
        GUI-only mode instead of crashing.
        """
        model_id = self.config.get().monitor_model
        logger.debug("Detecting monitor (configured model: %s)...", model_id)

        self.monitor = create_monitor(model_id, self.registry)
        if self.monitor is None:
            logger.warning("No implementation available for monitor '%s'", model_id)
            return

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

    def _get_monitor_display_names(self) -> dict:
        """Get {registry_id: model_name} for every monitor definition known to the registry."""
        return {model_id: info.model_name for model_id, info in
                zip(self.registry.list_ids(), self.registry.list_all())}

    def _get_shortcuts_dict(self) -> dict:
        """Get the current shortcut bindings as plain dicts, for the Settings dialog."""
        config = self.config.get()
        result = {}
        default_mod = ["ctrl", "super"]
        if self.monitor:
            for idx, inp in enumerate(self.monitor.info.inputs, start=1):
                action = f"switch_input_{inp.id}"
                result[action] = {"modifiers": default_mod, "key": str(idx)}
        result["cycle_profile"] = {"modifiers": default_mod, "key": "p"}
        for action, cfg in config.shortcuts.items():
            result[action] = {"modifiers": cfg.modifiers, "key": cfg.key}
        return result

    def _setup_shortcuts(self) -> None:
        """
        Register keyboard shortcuts.

        Builds one shortcut per input source (switch_input_<id>) and one for
        profile cycling, using persisted config values when present, falling
        back to sane defaults otherwise. This makes every input/profile
        independently rebindable (req #6) instead of hardcoding only two inputs.
        """
        config = self.config.get()
        default_mod = ["ctrl", "super"]

        # Build default bindings: one numbered key per known input, "p" to cycle profiles.
        shortcuts_config = {}
        if self.monitor:
            for idx, inp in enumerate(self.monitor.info.inputs, start=1):
                action = f"switch_input_{inp.id}"
                shortcuts_config[action] = {"modifiers": default_mod, "key": str(idx)}
        shortcuts_config["cycle_profile"] = {"modifiers": default_mod, "key": "p"}

        # Override with any user-customized shortcuts from config.
        if config.shortcuts:
            for action, shortcut_cfg in config.shortcuts.items():
                shortcuts_config[action] = {
                    "modifiers": shortcut_cfg.modifiers,
                    "key": shortcut_cfg.key,
                }

        self.shortcuts.clear()  # Remove any previously-registered bindings before re-registering.
        for action, cfg in shortcuts_config.items():
            try:
                shortcut = Shortcut(cfg["modifiers"], cfg["key"])
                if action.startswith("switch_input_"):
                    input_id = action[len("switch_input_"):]
                    self.shortcuts.register(shortcut, lambda i=input_id: self._switch_input(i))
                elif action == "cycle_profile":
                    self.shortcuts.register(shortcut, self._cycle_profile)
                logger.debug("Registered shortcut: %s -> %s", action, shortcut)
            except Exception as e:
                logger.error("Failed to register shortcut '%s': %s", action, e)

    def _switch_input(self, source_id: str) -> None:
        """Switch monitor input source."""
        if not self.monitor:
            logger.warning("Monitor not connected")
            self.gui.show_error(
                "Monitor not connected",
                "Cannot switch input: no monitor is currently connected.\n\n"
                "Check that the monitor is powered on, the USB cable is plugged "
                "in, and that your user has permission to access the HID device "
                "(see the udev rule in the project's 90-msi-monitor.rules).",
            )
            return

        try:
            if self.monitor.set_input(source_id):
                self.config.set_input(source_id, self._get_input_display_names().get(source_id, source_id))
                logger.info("Switched input to: %s", source_id)
                self.gui.update_menu(
                    inputs=self._get_input_display_names(),
                    profiles=self._get_profile_display_names(),
                    current_input=self.config.get().selected_input_id,
                    current_profile=self.config.get().selected_profile_id,
                    monitors=self._get_monitor_display_names(),
                    current_monitor=self.config.get().monitor_model,
                    shortcuts=self._get_shortcuts_dict(),
                )
            else:
                logger.warning("Failed to switch input")
                self.gui.show_error(
                    "Input switch failed",
                    f"The monitor rejected the request to switch to '{source_id}'. "
                    "Check the connection and try again.",
                )
        except Exception as e:
            logger.error("Error switching input: %s", e)
            self.gui.show_error("Input switch failed", f"An error occurred while switching input:\n{e}")

    def _cycle_profile(self) -> None:
        """Cycle to next profile."""
        if not self.monitor:
            logger.warning("Monitor not connected")
            self.gui.show_error(
                "Monitor not connected",
                "Cannot cycle profile: no monitor is currently connected.",
            )
            return

        try:
            if self.monitor.next_profile():
                logger.info("Cycled to next profile")
                new_profile_id = self.monitor.get_current_profile()
                if new_profile_id:
                    display_name = self._get_profile_display_names().get(new_profile_id, new_profile_id)
                    self.config.set_profile(new_profile_id, display_name)
                    self.gui.update_menu(
                        inputs=self._get_input_display_names(),
                        profiles=self._get_profile_display_names(),
                        current_input=self.config.get().selected_input_id,
                        current_profile=self.config.get().selected_profile_id,
                        monitors=self._get_monitor_display_names(),
                        current_monitor=self.config.get().monitor_model,
                        shortcuts=self._get_shortcuts_dict(),
                    )
            else:
                logger.warning("Failed to cycle profile")
                self.gui.show_error("Profile cycle failed", "The monitor rejected the request to cycle profiles.")
        except Exception as e:
            logger.error("Error cycling profile: %s", e)
            self.gui.show_error("Profile cycle failed", f"An error occurred while cycling profile:\n{e}")

    def _on_input_changed(self, input_id: str) -> None:
        """Callback when user selects input from tray menu."""
        logger.debug("User selected input: %s", input_id)
        self._switch_input(input_id)

    def _on_profile_changed(self, profile_id: str) -> None:
        """Callback when user selects a specific profile from the tray menu."""
        logger.debug("User selected profile: %s", profile_id)
        if not self.monitor:
            logger.warning("Monitor not connected")
            self.gui.show_error(
                "Monitor not connected",
                "Cannot switch profile: no monitor is currently connected.\n\n"
                "Check that the monitor is powered on, the USB cable is plugged "
                "in, and that your user has permission to access the HID device.",
            )
            return

        try:
            if self.monitor.set_profile(profile_id):
                display_name = self._get_profile_display_names().get(profile_id, profile_id)
                self.config.set_profile(profile_id, display_name)
                logger.info("Profile switched to: %s", profile_id)
                self.gui.update_menu(
                    inputs=self._get_input_display_names(),
                    profiles=self._get_profile_display_names(),
                    current_input=self.config.get().selected_input_id,
                    current_profile=self.config.get().selected_profile_id,
                    monitors=self._get_monitor_display_names(),
                    current_monitor=self.config.get().monitor_model,
                    shortcuts=self._get_shortcuts_dict(),
                )
            else:
                logger.warning("Failed to switch profile to %s", profile_id)
                self.gui.show_error(
                    "Profile switch failed",
                    f"The monitor rejected the request to switch to profile '{profile_id}'.",
                )
        except Exception as e:
            logger.error("Error switching profile: %s", e)
            self.gui.show_error("Profile switch failed", f"An error occurred while switching profile:\n{e}")

    def _on_settings_changed(self, settings: dict) -> None:
        """
        Callback when the user saves changes in the Settings dialog.

        `settings` is expected to contain:
          - "input_names": {input_id: new_display_name}
          - "profile_names": {profile_id: new_display_name}
          - "shortcuts": {action: {"modifiers": [...], "key": "..."}}
        Persists everything via ConfigManager and rebuilds the tray menu +
        keyboard shortcut bindings so changes take effect immediately without
        restarting the app.
        """
        for input_id, name in settings.get("input_names", {}).items():
            self.config.set_custom_input_name(input_id, name)
        for profile_id, name in settings.get("profile_names", {}).items():
            self.config.set_custom_profile_name(profile_id, name)
        for action, cfg in settings.get("shortcuts", {}).items():
            self.config.set_shortcut(action, cfg.get("modifiers", []), cfg.get("key", ""))

        logger.info("Settings saved; refreshing menu and shortcuts")

        # Refresh the tray menu with new display names.
        self.gui.update_menu(
            inputs=self._get_input_display_names(),
            profiles=self._get_profile_display_names(),
            current_input=self.config.get().selected_input_id,
            current_profile=self.config.get().selected_profile_id,
            monitors=self._get_monitor_display_names(),
            current_monitor=self.config.get().monitor_model,
            shortcuts=self._get_shortcuts_dict(),
        )
        # Re-register keyboard shortcuts with the new bindings.
        self._setup_shortcuts()

    def _on_monitor_selected(self, model_id: str) -> None:
        """
        Callback when the user picks a different monitor model.

        Persists the choice (req #12: selection is persistent until changed),
        disconnects the current monitor, and reconnects using the new model.
        """
        logger.info("User selected monitor model: %s", model_id)
        self.config.set_monitor(model_id)

        if self.monitor and self.monitor.is_open:
            try:
                self.monitor.close()
            except Exception as e:
                logger.warning("Error closing previous monitor: %s", e)

        self._connect_monitor()
        self.gui.update_menu(
            inputs=self._get_input_display_names(),
            profiles=self._get_profile_display_names(),
            current_input=self.config.get().selected_input_id,
            current_profile=self.config.get().selected_profile_id,
            monitors=self._get_monitor_display_names(),
            current_monitor=self.config.get().monitor_model,
            shortcuts=self._get_shortcuts_dict(),
        )
        self._setup_shortcuts()

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
