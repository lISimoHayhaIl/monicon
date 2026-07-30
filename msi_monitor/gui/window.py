"""
Modern PyQt6-based system tray GUI for Monicon.

Features:
- System tray icon with context menu
- Input source and profile selection menus
- Settings dialog for keyboard shortcuts and custom names
- Minimize to tray on window close
- Confirmation dialog on quit
"""

import logging
import sys
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)


class MoniconicoTrayWindow:
    """
    Main system tray window with PyQt6.
    
    Provides:
    - Tray icon with context menu
    - Settings dialog
    - Input/profile selection menus
    """

    def __init__(self, app_name: str = "Monicon"):
        """Initialize the tray window."""
        try:
            from PyQt6.QtWidgets import (
                QApplication, QSystemTrayIcon, QMainWindow, QMenu, QWidget,
                QVBoxLayout, QDialog, QLabel, QPushButton, QComboBox,
                QMessageBox, QKeySequenceEdit, QSpinBox, QCheckBox,
                QGridLayout, QLineEdit, QFormLayout
            )
            from PyQt6.QtGui import QIcon, QAction, QColor
            from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize
            from PyQt6.QtSvg import QSvgWidget
        except ImportError as e:
            raise ImportError(f"PyQt6 not installed: {e}. Run: pip install PyQt6")

        self._QtWidgets = {
            'QApplication': QApplication,
            'QSystemTrayIcon': QSystemTrayIcon,
            'QMainWindow': QMainWindow,
            'QMenu': QMenu,
            'QWidget': QWidget,
            'QVBoxLayout': QVBoxLayout,
            'QDialog': QDialog,
            'QLabel': QLabel,
            'QPushButton': QPushButton,
            'QComboBox': QComboBox,
            'QMessageBox': QMessageBox,
            'QKeySequenceEdit': QKeySequenceEdit,
            'QSpinBox': QSpinBox,
            'QCheckBox': QCheckBox,
            'QGridLayout': QGridLayout,
            'QLineEdit': QLineEdit,
            'QFormLayout': QFormLayout,
        }
        self._QtGui = {'QIcon': QIcon, 'QAction': QAction, 'QColor': QColor}
        self._QtCore = {'Qt': Qt, 'QSize': QSize}

        self.app_name = app_name
        self._app = None
        self._main_window = None
        self._tray_icon = None
        self._settings_dialog = None

        # Callbacks
        self._on_input_changed: Optional[Callable[[str], None]] = None
        self._on_profile_changed: Optional[Callable[[str], None]] = None
        self._on_quit_requested: Optional[Callable[[], None]] = None
        self._on_settings_changed: Optional[Callable[[Dict], None]] = None

        # Data
        self._inputs: Dict[str, str] = {}  # id -> display_name
        self._profiles: Dict[str, str] = {}  # id -> display_name

    def initialize(
        self,
        inputs: Dict[str, str],
        profiles: Dict[str, str],
        current_input: Optional[str] = None,
        current_profile: Optional[str] = None,
    ) -> None:
        """
        Initialize the GUI with monitor inputs and profiles.
        
        Args:
            inputs: Dict of input_id -> display_name
            profiles: Dict of profile_id -> display_name
            current_input: Currently selected input ID
            current_profile: Currently selected profile ID
        """
        self._inputs = inputs
        self._profiles = profiles
        self._current_input = current_input
        self._current_profile = current_profile

        # Create application
        if not self._app:
            self._app = self._QtWidgets['QApplication'].instance()
            if not self._app:
                self._app = self._QtWidgets['QApplication'](sys.argv)

        # Create main window (hidden)
        self._main_window = self._QtWidgets['QMainWindow']()
        self._main_window.setWindowTitle(self.app_name)
        self._main_window.closeEvent = self._on_window_close

        # Create tray icon
        self._tray_icon = self._QtWidgets['QSystemTrayIcon'](self._main_window)
        self._setup_tray_menu()
        self._tray_icon.show()

        logger.info("GUI initialized")

    def _setup_tray_menu(self) -> None:
        """Build the tray context menu with inputs and profiles."""
        menu = self._QtWidgets['QMenu']()

        # --- Show Window ---
        show_action = self._QtGui['QAction']("Show Window")
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        # --- Input Sources ---
        if self._inputs:
            input_menu = menu.addMenu("Input Source")
            for input_id, input_name in self._inputs.items():
                action = self._QtGui['QAction'](input_name)
                action.triggered.connect(
                    lambda checked=False, _id=input_id: self._on_input_selected(_id)
                )
                if input_id == self._current_input:
                    action.setCheckable(True)
                    action.setChecked(True)
                input_menu.addAction(action)

        # --- Profiles ---
        if self._profiles:
            profile_menu = menu.addMenu("Profile")
            for profile_id, profile_name in self._profiles.items():
                action = self._QtGui['QAction'](profile_name)
                action.triggered.connect(
                    lambda checked=False, _id=profile_id: self._on_profile_selected(_id)
                )
                if profile_id == self._current_profile:
                    action.setCheckable(True)
                    action.setChecked(True)
                profile_menu.addAction(action)

        menu.addSeparator()

        # --- Settings ---
        settings_action = self._QtGui['QAction']("Settings...")
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        # --- Quit ---
        quit_action = self._QtGui['QAction']("Quit")
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray_icon.setContextMenu(menu)

    def _show_window(self) -> None:
        """Show/restore the main window."""
        if self._main_window:
            self._main_window.showNormal()
            self._main_window.raise_()
            self._main_window.activateWindow()

    def _on_window_close(self, event) -> None:
        """Handle window close event - minimize to tray."""
        self._main_window.hide()
        event.ignore()

    def _on_input_selected(self, input_id: str) -> None:
        """User selected an input source."""
        logger.debug("Input selected: %s", input_id)
        if self._on_input_changed:
            self._on_input_changed(input_id)

    def _on_profile_selected(self, profile_id: str) -> None:
        """User selected a profile."""
        logger.debug("Profile selected: %s", profile_id)
        if self._on_profile_changed:
            self._on_profile_changed(profile_id)

    def _show_settings(self) -> None:
        """Show the settings dialog."""
        if not self._settings_dialog:
            self._settings_dialog = self._SettingsDialog(
                self._main_window,
                self._inputs,
                self._profiles,
            )

        self._settings_dialog.exec()

    def _quit_app(self) -> None:
        """Request quit with confirmation."""
        reply = self._QtWidgets['QMessageBox'].question(
            self._main_window,
            "Quit Monicon",
            "Are you sure you want to quit?",
            self._QtWidgets['QMessageBox'].StandardButton.Yes |
            self._QtWidgets['QMessageBox'].StandardButton.No,
            self._QtWidgets['QMessageBox'].StandardButton.No,
        )
        if reply == self._QtWidgets['QMessageBox'].StandardButton.Yes:
            if self._on_quit_requested:
                self._on_quit_requested()
            self._app.quit()

    def set_on_input_changed(self, callback: Callable[[str], None]) -> None:
        """Register callback for input selection."""
        self._on_input_changed = callback

    def set_on_profile_changed(self, callback: Callable[[str], None]) -> None:
        """Register callback for profile selection."""
        self._on_profile_changed = callback

    def set_on_quit_requested(self, callback: Callable[[], None]) -> None:
        """Register callback for quit request."""
        self._on_quit_requested = callback

    def set_on_settings_changed(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for settings changes."""
        self._on_settings_changed = callback

    def run(self) -> int:
        """Run the Qt event loop."""
        if self._app:
            return self._app.exec()
        return 1

    def quit(self) -> None:
        """Quit the application."""
        if self._app:
            self._app.quit()

    # ========================================================================
    #  Settings Dialog
    # ========================================================================

    class _SettingsDialog:
        """Settings/preferences dialog."""

        def __init__(self, parent, inputs: Dict[str, str], profiles: Dict[str, str]):
            """Initialize settings dialog."""
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton
            from PyQt6.QtCore import Qt

            self.dialog = QDialog(parent)
            self.dialog.setWindowTitle("Monicon Settings")
            self.dialog.setGeometry(100, 100, 400, 300)

            layout = QVBoxLayout()
            form_layout = QFormLayout()

            # Custom input names
            self.input_edits = {}
            if inputs:
                label = QDialog().label() if hasattr(QDialog, 'label') else None
                for input_id, input_name in inputs.items():
                    edit = QLineEdit(input_name)
                    self.input_edits[input_id] = edit
                    form_layout.addRow(f"Input: {input_id}", edit)

            # Custom profile names
            self.profile_edits = {}
            if profiles:
                for profile_id, profile_name in profiles.items():
                    edit = QLineEdit(profile_name)
                    self.profile_edits[profile_id] = edit
                    form_layout.addRow(f"Profile: {profile_id}", edit)

            layout.addLayout(form_layout)

            # OK / Cancel buttons
            buttons_layout = QVBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            ok_button.clicked.connect(self.dialog.accept)
            cancel_button.clicked.connect(self.dialog.reject)
            buttons_layout.addWidget(ok_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)

            self.dialog.setLayout(layout)

        def exec(self) -> int:
            """Show the dialog and wait for user input."""
            return self.dialog.exec()
