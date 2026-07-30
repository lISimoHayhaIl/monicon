"""
System tray GUI for Monicon.

Modern, minimal PyQt6-based interface with system tray icon.
Supports left-click menu (input/profile selection), minimize to tray, and global keybindings.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class TrayIcon:
    """
    System tray icon manager.
    
    Handles tray icon display, context menu, and window minimize/restore.
    Uses PyQt6 for cross-desktop compatibility.
    """

    def __init__(self, app_name: str = "Monicon"):
        """Initialize tray icon."""
        try:
            from PyQt6.QtWidgets import (
                QApplication, QSystemTrayIcon, QMainWindow, QMenu, QWidget, QVBoxLayout
            )
            from PyQt6.QtGui import QIcon, QAction
            from PyQt6.QtCore import Qt, QTimer
        except ImportError:
            raise ImportError("PyQt6 not installed. Run: pip install PyQt6")

        self._QtWidgets = type('QtWidgets', (), {
            'QApplication': QApplication,
            'QSystemTrayIcon': QSystemTrayIcon,
            'QMainWindow': QMainWindow,
            'QMenu': QMenu,
            'QWidget': QWidget,
            'QVBoxLayout': QVBoxLayout,
        })()
        self._QtGui = type('QtGui', (), {'QIcon': QIcon, 'QAction': QAction})()
        self._QtCore = type('QtCore', (), {'Qt': Qt, 'QTimer': QTimer})()

        self.app_name = app_name
        self._app = None
        self._tray_icon = None
        self._window = None
        self._on_quit_callback: Optional[Callable] = None
        self._on_settings_callback: Optional[Callable] = None

    def initialize(self, window, on_quit: Callable, on_settings: Callable) -> None:
        """
        Initialize the tray system.
        
        Args:
            window: The main window widget
            on_quit: Callback when user requests quit
            on_settings: Callback to show settings menu
        """
        if not self._app:
            self._app = self._QtWidgets.QApplication.instance()
            if not self._app:
                self._app = self._QtWidgets.QApplication(sys.argv)

        self._window = window
        self._on_quit_callback = on_quit
        self._on_settings_callback = on_settings

        # Create tray icon
        self._tray_icon = self._QtWidgets.QSystemTrayIcon()
        self._setup_tray_menu()
        self._tray_icon.show()

        logger.info("System tray initialized")

    def _setup_tray_menu(self) -> None:
        """Build the context menu for the tray icon."""
        if not self._tray_icon:
            return

        menu = self._QtWidgets.QMenu()

        # Show/hide window
        show_action = self._QtGui.QAction("Show")
        show_action.triggered.connect(self._on_show)
        menu.addAction(show_action)

        # Settings
        settings_action = self._QtGui.QAction("Settings")
        settings_action.triggered.connect(self._on_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Quit
        quit_action = self._QtGui.QAction("Quit")
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray_icon.setContextMenu(menu)

    def _on_show(self) -> None:
        """Show/restore the main window."""
        if self._window:
            self._window.showNormal()
            self._window.raise_()
            self._window.activateWindow()

    def _on_settings(self) -> None:
        """Open settings menu."""
        if self._on_settings_callback:
            self._on_settings_callback()

    def _on_quit(self) -> None:
        """Request quit."""
        if self._on_quit_callback:
            self._on_quit_callback()

    def set_icon(self, icon_path: Optional[str]) -> None:
        """Set the tray icon image."""
        if not self._tray_icon:
            return
        if icon_path and Path(icon_path).exists():
            self._tray_icon.setIcon(self._QtGui.QIcon(icon_path))

    def set_tooltip(self, text: str) -> None:
        """Set the tray icon tooltip."""
        if self._tray_icon:
            self._tray_icon.setToolTip(text)

    def run(self) -> int:
        """Start the Qt event loop."""
        if self._app:
            return self._app.exec()
        return 1

    def quit(self) -> None:
        """Quit the application."""
        if self._app:
            self._app.quit()
