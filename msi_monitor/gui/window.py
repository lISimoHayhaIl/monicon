"""
Modern PyQt6-based system tray GUI for Monicon.

Features:
- System tray icon (with a real Monicon icon) and left/right-click context menu
- Input source, profile, and monitor-model selection menus
- Settings dialog for keyboard shortcuts and custom names
- Minimize to tray on window close; left-click also offers "Restore & Quit"
- Confirmation dialog on quit
- Light, modern main window with quick-switch controls
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Directory containing the bundled icon assets (see msi_monitor/gui/assets/).
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Light, modern Qt stylesheet applied to the main window. Kept intentionally
# simple (flat colors, generous spacing) per requirement #7 ("nice, light and
# modern UI") without pulling in any external/paid theming library.
_LIGHT_QSS = """
QMainWindow, QDialog {
    background-color: #F7F8FA;
}
QLabel {
    color: #1F2430;
    font-size: 13px;
}
QLabel#Title {
    font-size: 18px;
    font-weight: 600;
    color: #1F5FE0;
}
QLabel#Subtitle {
    color: #6B7280;
    font-size: 12px;
}
QComboBox, QLineEdit, QKeySequenceEdit {
    background-color: #FFFFFF;
    border: 1px solid #D8DCE3;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 22px;
}
QPushButton {
    background-color: #1F5FE0;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #174ABF;
}
QPushButton#Secondary {
    background-color: #E7EBF3;
    color: #1F2430;
}
QPushButton#Secondary:hover {
    background-color: #DAE0EC;
}
"""


class MoniconicoTrayWindow:
    """
    Main system tray window with PyQt6.

    Provides:
    - Tray icon with context menu (also triggered on left-click)
    - A light modern main window with quick-switch controls
    - Settings dialog for renaming inputs/profiles and rebinding shortcuts
    """

    def __init__(self, app_name: str = "Monicon"):
        """Initialize the tray window."""
        try:
            from PyQt6.QtWidgets import (
                QApplication, QSystemTrayIcon, QMainWindow, QMenu, QWidget,
                QVBoxLayout, QHBoxLayout, QDialog, QLabel, QPushButton, QComboBox,
                QMessageBox, QKeySequenceEdit, QSpinBox, QCheckBox,
                QGridLayout, QLineEdit, QFormLayout, QScrollArea, QTabWidget,
            )
            from PyQt6.QtGui import QIcon, QAction, QColor, QKeySequence, QCursor
            from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize
        except ImportError as e:
            raise ImportError(f"PyQt6 not installed: {e}. Run: pip install PyQt6")

        self._QtWidgets = {
            'QApplication': QApplication,
            'QSystemTrayIcon': QSystemTrayIcon,
            'QMainWindow': QMainWindow,
            'QMenu': QMenu,
            'QWidget': QWidget,
            'QVBoxLayout': QVBoxLayout,
            'QHBoxLayout': QHBoxLayout,
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
            'QScrollArea': QScrollArea,
            'QTabWidget': QTabWidget,
        }
        self._QtGui = {
            'QIcon': QIcon, 'QAction': QAction, 'QColor': QColor,
            'QKeySequence': QKeySequence, 'QCursor': QCursor,
        }
        self._QtCore = {'Qt': Qt, 'QSize': QSize}

        self.app_name = app_name
        self._app = None
        self._main_window = None
        self._tray_icon = None
        self._settings_dialog = None
        self._icon = None

        # Callbacks
        self._on_input_changed: Optional[Callable[[str], None]] = None
        self._on_profile_changed: Optional[Callable[[str], None]] = None
        self._on_quit_requested: Optional[Callable[[], None]] = None
        self._on_settings_changed: Optional[Callable[[Dict], None]] = None
        self._on_monitor_selected: Optional[Callable[[str], None]] = None

        # Data
        self._inputs: Dict[str, str] = {}     # id -> display_name
        self._profiles: Dict[str, str] = {}   # id -> display_name
        self._monitors: Dict[str, str] = {}   # registry_id -> model_name
        self._shortcuts: Dict[str, Dict] = {} # action -> {"modifiers": [...], "key": "..."}
        self._current_input: Optional[str] = None
        self._current_profile: Optional[str] = None
        self._current_monitor: Optional[str] = None

        # Widgets in the main window that need refreshing on update_menu()
        self._input_combo = None
        self._profile_combo = None
        self._monitor_combo = None
        self._status_label = None

    # ------------------------------------------------------------------
    #  Initialization
    # ------------------------------------------------------------------

    def _load_icon(self):
        """
        Load the Monicon application/tray icon.

        Prefers the SVG (Qt6 renders it at any resolution via QtSvg), falling
        back to the bundled PNG if SVG support isn't available, so a valid
        icon is always shown instead of the blank/default one.
        """
        svg_path = _ASSETS_DIR / "monicon.svg"
        png_path = _ASSETS_DIR / "monicon-64.png"
        QIcon = self._QtGui['QIcon']
        if svg_path.exists():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon
        if png_path.exists():
            return QIcon(str(png_path))
        logger.warning("No icon assets found in %s; tray icon will be blank", _ASSETS_DIR)
        return QIcon()

    def initialize(
        self,
        inputs: Dict[str, str],
        profiles: Dict[str, str],
        current_input: Optional[str] = None,
        current_profile: Optional[str] = None,
        monitors: Optional[Dict[str, str]] = None,
        current_monitor: Optional[str] = None,
        shortcuts: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """
        Initialize the GUI with monitor inputs, profiles, and available monitor models.

        Args:
            inputs: Dict of input_id -> display_name
            profiles: Dict of profile_id -> display_name
            current_input: Currently selected input ID
            current_profile: Currently selected profile ID
            monitors: Dict of registry_id -> model_name (all monitors known to the registry)
            current_monitor: Currently selected monitor registry id
            shortcuts: Dict of action -> {"modifiers": [...], "key": "..."} for the Settings dialog
        """
        self._inputs = inputs
        self._profiles = profiles
        self._monitors = monitors or {}
        self._shortcuts = shortcuts or {}
        self._current_input = current_input
        self._current_profile = current_profile
        self._current_monitor = current_monitor

        # Create application
        if not self._app:
            self._app = self._QtWidgets['QApplication'].instance()
            if not self._app:
                self._app = self._QtWidgets['QApplication'](sys.argv)

        # Set application/desktop identity so the tray icon, window manager,
        # and notification popups show "Monicon" instead of falling back to
        # the interpreter's script name (e.g. "cli.py") — this is what a
        # StatusNotifierItem's Title property derives from if left unset.
        self._app.setApplicationName(self.app_name)
        self._app.setApplicationDisplayName(self.app_name)
        self._app.setDesktopFileName("monicon")

        self._icon = self._load_icon()
        # Keep the app alive in the tray after the last window closes.
        self._app.setQuitOnLastWindowClosed(False)

        self._build_main_window()
        self._build_tray_icon()

        logger.info("GUI initialized")

    def _build_main_window(self) -> None:
        """Build the light, modern main window with quick-switch controls."""
        QMainWindow = self._QtWidgets['QMainWindow']
        QWidget = self._QtWidgets['QWidget']
        QVBoxLayout = self._QtWidgets['QVBoxLayout']
        QHBoxLayout = self._QtWidgets['QHBoxLayout']
        QLabel = self._QtWidgets['QLabel']
        QComboBox = self._QtWidgets['QComboBox']
        QPushButton = self._QtWidgets['QPushButton']
        Qt = self._QtCore['Qt']

        self._main_window = QMainWindow()
        self._main_window.setWindowTitle(self.app_name)
        self._main_window.setWindowIcon(self._icon)
        self._main_window.resize(420, 320)
        self._main_window.setStyleSheet(_LIGHT_QSS)
        # Minimize-to-tray on close (requirement #8): intercept the close event.
        self._main_window.closeEvent = self._on_window_close

        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel(self.app_name)
        title.setObjectName("Title")
        subtitle = QLabel("MSI monitor input & profile control")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self._status_label = QLabel()
        self._status_label.setObjectName("Subtitle")
        layout.addWidget(self._status_label)

        # Monitor selector
        monitor_row = QHBoxLayout()
        monitor_row.addWidget(QLabel("Monitor:"))
        self._monitor_combo = QComboBox()
        monitor_row.addWidget(self._monitor_combo, 1)
        layout.addLayout(monitor_row)

        # Input selector + apply
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Input source:"))
        self._input_combo = QComboBox()
        input_row.addWidget(self._input_combo, 1)
        apply_input_btn = QPushButton("Switch")
        apply_input_btn.clicked.connect(self._apply_input_from_combo)
        input_row.addWidget(apply_input_btn)
        layout.addLayout(input_row)

        # Profile selector + apply
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self._profile_combo = QComboBox()
        profile_row.addWidget(self._profile_combo, 1)
        apply_profile_btn = QPushButton("Switch")
        apply_profile_btn.clicked.connect(self._apply_profile_from_combo)
        profile_row.addWidget(apply_profile_btn)
        layout.addLayout(profile_row)

        layout.addStretch(1)

        # Bottom action row
        bottom_row = QHBoxLayout()
        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("Secondary")
        settings_btn.clicked.connect(self._show_settings)
        minimize_btn = QPushButton("Minimize to tray")
        minimize_btn.setObjectName("Secondary")
        minimize_btn.clicked.connect(lambda: self._main_window.hide())
        bottom_row.addWidget(settings_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(minimize_btn)
        layout.addLayout(bottom_row)

        central.setLayout(layout)
        self._main_window.setCentralWidget(central)

        self._monitor_combo.currentIndexChanged.connect(self._on_monitor_combo_changed)
        self._refresh_widgets()

    def _build_tray_icon(self) -> None:
        """Create the system tray icon and its menu."""
        self._tray_icon = self._QtWidgets['QSystemTrayIcon'](self._icon, self._main_window)
        self._tray_icon.setToolTip(self.app_name)
        self._setup_tray_menu()
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    # ------------------------------------------------------------------
    #  Tray menu
    # ------------------------------------------------------------------

    def _setup_tray_menu(self) -> None:
        """Build the tray context menu with inputs, profiles, and monitors."""
        QMenu = self._QtWidgets['QMenu']
        QAction = self._QtGui['QAction']

        menu = QMenu()

        show_action = QAction("Show Window", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        # --- Input Sources (requirement #3/#4: left-click accessible selection) ---
        if self._inputs:
            input_menu = menu.addMenu("Input Source")
            for input_id, input_name in self._inputs.items():
                action = QAction(input_name, menu)
                action.setCheckable(True)
                action.setChecked(input_id == self._current_input)
                action.triggered.connect(
                    lambda checked=False, _id=input_id: self._on_input_selected(_id)
                )
                input_menu.addAction(action)

        # --- Profiles ---
        if self._profiles:
            profile_menu = menu.addMenu("Profile")
            for profile_id, profile_name in self._profiles.items():
                action = QAction(profile_name, menu)
                action.setCheckable(True)
                action.setChecked(profile_id == self._current_profile)
                action.triggered.connect(
                    lambda checked=False, _id=profile_id: self._on_profile_selected(_id)
                )
                profile_menu.addAction(action)

        # --- Monitor selection (requirement #12: persistent monitor selection) ---
        if self._monitors:
            monitor_menu = menu.addMenu("Monitor")
            for model_id, model_name in self._monitors.items():
                action = QAction(model_name, menu)
                action.setCheckable(True)
                action.setChecked(model_id == self._current_monitor)
                action.triggered.connect(
                    lambda checked=False, _id=model_id: self._on_monitor_menu_selected(_id)
                )
                monitor_menu.addAction(action)

        menu.addSeparator()

        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        # Requirement #10: left-click menu also offers restore-then-quit.
        restore_quit_action = QAction("Restore Window && Quit", menu)
        restore_quit_action.triggered.connect(self._restore_and_quit)
        menu.addAction(restore_quit_action)

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray_icon.setContextMenu(menu)

    def update_menu(
        self,
        inputs: Dict[str, str],
        profiles: Dict[str, str],
        current_input: Optional[str] = None,
        current_profile: Optional[str] = None,
        monitors: Optional[Dict[str, str]] = None,
        current_monitor: Optional[str] = None,
        shortcuts: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """Rebuild the tray menu and main-window controls (called after settings/monitor changes)."""
        self._inputs = inputs
        self._profiles = profiles
        if monitors is not None:
            self._monitors = monitors
        if shortcuts is not None:
            self._shortcuts = shortcuts
        self._current_input = current_input
        self._current_profile = current_profile
        if current_monitor is not None:
            self._current_monitor = current_monitor

        if self._tray_icon:
            self._setup_tray_menu()
        self._refresh_widgets()

    def _refresh_widgets(self) -> None:
        """Sync the main-window combo boxes and status label with current state."""
        if self._monitor_combo is not None:
            self._monitor_combo.blockSignals(True)
            self._monitor_combo.clear()
            for model_id, model_name in self._monitors.items():
                self._monitor_combo.addItem(model_name, model_id)
            idx = self._monitor_combo.findData(self._current_monitor)
            if idx >= 0:
                self._monitor_combo.setCurrentIndex(idx)
            self._monitor_combo.blockSignals(False)

        if self._input_combo is not None:
            self._input_combo.clear()
            # The MSI protocol cannot report which input is actually active (it has
            # no working query command — confirmed against real hardware), so when
            # we don't know (current_input is None) we show an explicit "Unknown"
            # placeholder instead of silently defaulting to whichever input happens
            # to be first in the list, which would misinform the user.
            if self._current_input is None:
                self._input_combo.addItem("Unknown (select to set)", None)
            for input_id, name in self._inputs.items():
                self._input_combo.addItem(name, input_id)
            idx = self._input_combo.findData(self._current_input)
            if idx >= 0:
                self._input_combo.setCurrentIndex(idx)

        if self._profile_combo is not None:
            self._profile_combo.clear()
            if self._current_profile is None:
                self._profile_combo.addItem("Unknown (select to set)", None)
            for profile_id, name in self._profiles.items():
                self._profile_combo.addItem(name, profile_id)
            idx = self._profile_combo.findData(self._current_profile)
            if idx >= 0:
                self._profile_combo.setCurrentIndex(idx)

        if self._status_label is not None:
            monitor_name = self._monitors.get(self._current_monitor, "No monitor connected")
            input_name = self._inputs.get(self._current_input, "Unknown") if self._current_input else "Unknown"
            self._status_label.setText(f"Connected: {monitor_name}  |  Input: {input_name}")

    # ------------------------------------------------------------------
    #  Window / tray behaviour
    # ------------------------------------------------------------------

    def _show_window(self) -> None:
        """Show/restore the main window (requirement #10: left-click restore)."""
        if self._main_window:
            self._main_window.showNormal()
            self._main_window.raise_()
            self._main_window.activateWindow()

    def _on_window_close(self, event) -> None:
        """Handle window close event - minimize to tray instead of exiting (requirement #8)."""
        self._main_window.hide()
        event.ignore()

    def _on_tray_activated(self, reason) -> None:
        """
        Handle tray icon activation.

        A single left-click (Trigger) pops up the same menu used for
        right-click, satisfying requirement #4 ("settings profiles available
        upon left-click") uniformly across desktop environments — some DEs
        only show QSystemTrayIcon context menus on right-click by default.
        """
        QSystemTrayIcon = self._QtWidgets['QSystemTrayIcon']
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.Context,
        ):
            menu = self._tray_icon.contextMenu()
            if menu:
                menu.popup(self._QtGui['QCursor'].pos())

    def _on_input_selected(self, input_id: str) -> None:
        """User selected an input source from a menu."""
        logger.debug("Input selected: %s", input_id)
        self._current_input = input_id
        if self._on_input_changed:
            self._on_input_changed(input_id)

    def _on_profile_selected(self, profile_id: str) -> None:
        """User selected a profile from a menu."""
        logger.debug("Profile selected: %s", profile_id)
        self._current_profile = profile_id
        if self._on_profile_changed:
            self._on_profile_changed(profile_id)

    def _on_monitor_menu_selected(self, model_id: str) -> None:
        """User selected a monitor model from the tray menu."""
        logger.debug("Monitor selected: %s", model_id)
        self._current_monitor = model_id
        if self._on_monitor_selected:
            self._on_monitor_selected(model_id)

    def _on_monitor_combo_changed(self, index: int) -> None:
        """User selected a monitor model from the main window combo box."""
        if index < 0 or self._monitor_combo is None:
            return
        model_id = self._monitor_combo.itemData(index)
        if model_id and model_id != self._current_monitor:
            self._current_monitor = model_id
            if self._on_monitor_selected:
                self._on_monitor_selected(model_id)

    def _apply_input_from_combo(self) -> None:
        """Apply the input source chosen in the main window's combo box."""
        if self._input_combo is None or self._input_combo.count() == 0:
            return
        input_id = self._input_combo.currentData()
        if input_id:
            self._on_input_selected(input_id)

    def _apply_profile_from_combo(self) -> None:
        """Apply the profile chosen in the main window's combo box."""
        if self._profile_combo is None or self._profile_combo.count() == 0:
            return
        profile_id = self._profile_combo.currentData()
        if profile_id:
            self._on_profile_selected(profile_id)

    def _restore_and_quit(self) -> None:
        """Show the window, then run the normal (confirmed) quit flow (requirement #10)."""
        self._show_window()
        self._quit_app()

    def _quit_app(self) -> None:
        """Request quit with confirmation (requirement #9)."""
        QMessageBox = self._QtWidgets['QMessageBox']
        reply = QMessageBox.question(
            self._main_window,
            "Quit Monicon",
            "Are you sure you want to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._on_quit_requested:
                self._on_quit_requested()
            self._app.quit()

    def _show_settings(self) -> None:
        """Show the settings dialog (rebuilt fresh each time to reflect current state)."""
        self._settings_dialog = _SettingsDialog(
            self,
            self._main_window,
            self._inputs,
            self._profiles,
            self._shortcuts,
        )
        if self._settings_dialog.exec():
            result = self._settings_dialog.result_data()
            if self._on_settings_changed:
                self._on_settings_changed(result)

    # ------------------------------------------------------------------
    #  Callback registration
    # ------------------------------------------------------------------

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
        """Register callback for settings changes (custom names + shortcuts)."""
        self._on_settings_changed = callback

    def set_on_monitor_selected(self, callback: Callable[[str], None]) -> None:
        """Register callback for monitor model selection."""
        self._on_monitor_selected = callback

    # ------------------------------------------------------------------
    #  User feedback (errors / confirmations)
    # ------------------------------------------------------------------

    def show_error(self, title: str, message: str) -> None:
        """
        Show a blocking error dialog to the user.

        Previously, failures while switching input/profile (monitor not
        connected, HID write error, unsupported feature, etc.) were only
        written to the log file, so the user clicking "Switch" while the
        monitor was unreachable saw nothing happen at all. Every failure
        path in the application should call this so the user always gets
        visible feedback.
        """
        QMessageBox = self._QtWidgets['QMessageBox']
        parent = self._main_window if (self._main_window and self._main_window.isVisible()) else None
        QMessageBox.warning(parent, title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show a brief tray notification (falls back to a dialog if tray notifications are unavailable)."""
        if self._tray_icon is not None:
            QSystemTrayIcon = self._QtWidgets['QSystemTrayIcon']
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)
        else:
            QMessageBox = self._QtWidgets['QMessageBox']
            QMessageBox.information(self._main_window, title, message)

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> int:
        """Run the Qt event loop."""
        if self._app:
            return self._app.exec()
        return 1

    def quit(self) -> None:
        """Quit the application."""
        if self._app:
            self._app.quit()


# ==============================================================================
#  Shortcut string <-> config conversion helpers
# ==============================================================================

def _qkeysequence_to_config(seq_str: str) -> Tuple[List[str], str]:
    """
    Convert a Qt key-sequence string (e.g. "Ctrl+Meta+1") to our internal
    (modifiers, key) representation used by ShortcutManager/ConfigManager.
    """
    if not seq_str:
        return [], ""
    parts = [p.strip().lower() for p in seq_str.split('+') if p.strip()]
    if not parts:
        return [], ""
    key = parts[-1]
    modifiers = ["super" if m == "meta" else m for m in parts[:-1]]
    return modifiers, key


def _config_to_qkeysequence_str(modifiers: List[str], key: str) -> str:
    """Convert our internal (modifiers, key) representation to a Qt key-sequence string."""
    mod_map = {"super": "Meta", "ctrl": "Ctrl", "shift": "Shift", "alt": "Alt"}
    parts = [mod_map.get(m.lower(), m.capitalize()) for m in modifiers]
    parts.append(key.upper() if len(key) == 1 else key.capitalize())
    return "+".join(parts)


# ==============================================================================
#  Settings Dialog
# ==============================================================================

class _SettingsDialog:
    """
    Settings/preferences dialog.

    Lets the user rename input sources and profiles (requirement #5) and
    rebind the keyboard shortcut for each input/profile action (requirement
    #6). Changes are only applied when the user clicks Save.
    """

    def __init__(
        self,
        tray_window: "MoniconicoTrayWindow",
        parent,
        inputs: Dict[str, str],
        profiles: Dict[str, str],
        shortcuts: Dict[str, Dict],
    ):
        """Build the settings dialog UI from current inputs/profiles/shortcuts."""
        QDialog = tray_window._QtWidgets['QDialog']
        QVBoxLayout = tray_window._QtWidgets['QVBoxLayout']
        QHBoxLayout = tray_window._QtWidgets['QHBoxLayout']
        QFormLayout = tray_window._QtWidgets['QFormLayout']
        QLineEdit = tray_window._QtWidgets['QLineEdit']
        QPushButton = tray_window._QtWidgets['QPushButton']
        QLabel = tray_window._QtWidgets['QLabel']
        QKeySequenceEdit = tray_window._QtWidgets['QKeySequenceEdit']
        QTabWidget = tray_window._QtWidgets['QTabWidget']
        QWidget = tray_window._QtWidgets['QWidget']
        QKeySequence = tray_window._QtGui['QKeySequence']

        self._inputs = inputs
        self._profiles = profiles
        self._shortcuts = shortcuts

        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle("Monicon Settings")
        self.dialog.setMinimumWidth(420)
        self.dialog.setStyleSheet(_LIGHT_QSS)

        layout = QVBoxLayout()
        tabs = QTabWidget()

        # --- Names tab ---
        names_tab = QWidget()
        names_form = QFormLayout()
        self.input_edits: Dict[str, QLineEdit] = {}
        for input_id, name in inputs.items():
            edit = QLineEdit(name)
            self.input_edits[input_id] = edit
            names_form.addRow(f"Input '{input_id}':", edit)
        self.profile_edits: Dict[str, QLineEdit] = {}
        for profile_id, name in profiles.items():
            edit = QLineEdit(name)
            self.profile_edits[profile_id] = edit
            names_form.addRow(f"Profile '{profile_id}':", edit)
        names_tab.setLayout(names_form)
        tabs.addTab(names_tab, "Names")

        # --- Shortcuts tab ---
        shortcuts_tab = QWidget()
        shortcuts_form = QFormLayout()
        self.shortcut_edits: Dict[str, "QKeySequenceEdit"] = {}
        for input_id, name in inputs.items():
            action = f"switch_input_{input_id}"
            cfg = shortcuts.get(action, {})
            edit = QKeySequenceEdit()
            seq_str = _config_to_qkeysequence_str(cfg.get("modifiers", []), cfg.get("key", ""))
            if seq_str.strip("+"):
                edit.setKeySequence(QKeySequence(seq_str))
            self.shortcut_edits[action] = edit
            shortcuts_form.addRow(f"Switch to {name}:", edit)

        cfg = shortcuts.get("cycle_profile", {})
        profile_edit = QKeySequenceEdit()
        seq_str = _config_to_qkeysequence_str(cfg.get("modifiers", []), cfg.get("key", ""))
        if seq_str.strip("+"):
            profile_edit.setKeySequence(QKeySequence(seq_str))
        self.shortcut_edits["cycle_profile"] = profile_edit
        shortcuts_form.addRow("Cycle profile:", profile_edit)

        shortcuts_tab.setLayout(shortcuts_form)
        tabs.addTab(shortcuts_tab, "Shortcuts")

        layout.addWidget(tabs)

        # OK / Cancel buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("Secondary")
        save_button = QPushButton("Save")
        cancel_button.clicked.connect(self.dialog.reject)
        save_button.clicked.connect(self.dialog.accept)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(save_button)
        layout.addLayout(buttons_layout)

        self.dialog.setLayout(layout)

    def exec(self) -> int:
        """Show the dialog modally and wait for user input. Returns truthy if Saved."""
        return self.dialog.exec()

    def result_data(self) -> Dict:
        """
        Collect edited values after the dialog was accepted.

        Returns a dict with "input_names", "profile_names", and "shortcuts"
        keys, matching the format expected by
        MonitorApplicationGUI._on_settings_changed().
        """
        input_names = {iid: edit.text().strip() or self._inputs[iid]
                        for iid, edit in self.input_edits.items()}
        profile_names = {pid: edit.text().strip() or self._profiles[pid]
                          for pid, edit in self.profile_edits.items()}
        shortcuts = {}
        for action, edit in self.shortcut_edits.items():
            seq = edit.keySequence()
            if seq.isEmpty():
                continue
            modifiers, key = _qkeysequence_to_config(seq.toString())
            if key:
                shortcuts[action] = {"modifiers": modifiers, "key": key}
        return {
            "input_names": input_names,
            "profile_names": profile_names,
            "shortcuts": shortcuts,
        }
