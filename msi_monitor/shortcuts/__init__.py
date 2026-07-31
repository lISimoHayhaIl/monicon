"""
Global keyboard shortcut handling.

Captures system-wide keyboard events for triggering monitor control actions.
Uses pynput for cross-DE compatibility (works on any Linux desktop).
"""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Shortcut:
    """Represents a keyboard shortcut."""

    def __init__(self, modifiers: List[str], key: str):
        """
        Initialize shortcut.
        
        Args:
            modifiers: List of modifier keys (e.g., ["ctrl", "shift", "alt", "super"])
            key: The main key (e.g., "F1", "i", "p")
        """
        self.modifiers = set(m.lower() for m in modifiers)
        self.key = key.lower()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Shortcut):
            return False
        return self.modifiers == other.modifiers and self.key == other.key

    def __hash__(self) -> int:
        return hash((frozenset(self.modifiers), self.key))

    def __repr__(self) -> str:
        mod_str = "+".join(sorted(self.modifiers))
        if mod_str:
            return f"{mod_str}+{self.key}"
        return self.key


class IShortcutListener(ABC):
    """Interface for keyboard event listeners."""

    @abstractmethod
    def on_shortcut(self, shortcut: Shortcut) -> None:
        """Called when a registered shortcut is pressed."""
        pass


class ShortcutManager:
    """
    Manages global keyboard shortcuts.

    Uses pynput's Listener to capture system-wide keyboard events.
    Registers shortcuts and notifies listeners when they're pressed.
    """

    def __init__(self):
        """Initialize the shortcut manager."""
        try:
            from pynput import keyboard
            self._keyboard = keyboard
        except ImportError:
            raise ImportError("pynput not installed. Run: pip install pynput")

        self._listener: Optional[self._keyboard.Listener] = None
        self._shortcuts: Dict[Shortcut, List[Callable]] = {}
        self._pressed_keys: set = set()
        self._lock = threading.RLock()
        self._running = False

    def register(self, shortcut: Shortcut, callback: Callable[[], None]) -> None:
        """
        Register a shortcut with a callback.
        
        Args:
            shortcut: The Shortcut to listen for
            callback: Function to call when shortcut is pressed
        """
        with self._lock:
            if shortcut not in self._shortcuts:
                self._shortcuts[shortcut] = []
            self._shortcuts[shortcut].append(callback)
            logger.debug("Registered shortcut: %s", shortcut)

    def unregister(self, shortcut: Shortcut, callback: Callable[[], None]) -> None:
        """Unregister a shortcut callback."""
        with self._lock:
            if shortcut in self._shortcuts and callback in self._shortcuts[shortcut]:
                self._shortcuts[shortcut].remove(callback)
                logger.debug("Unregistered shortcut: %s", shortcut)

    def clear(self) -> None:
        """Remove all registered shortcut bindings (used when rebuilding shortcuts, e.g. after Settings changes)."""
        with self._lock:
            self._shortcuts.clear()
            logger.debug("Cleared all shortcut bindings")

    def start(self) -> None:
        """Start listening for keyboard events."""
        if self._running:
            logger.debug("Shortcut listener already running")
            return

        self._pressed_keys.clear()
        self._listener = self._keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        self._running = True
        logger.info("Shortcut listener started")

    def stop(self) -> None:
        """
        Stop listening for keyboard events.

        On the X11 backend, pynput's Listener.stop() can raise AttributeError
        if the listener thread hasn't finished initializing its internal
        display-record context yet (e.g. stop() called immediately after
        start(), such as when the user quits right after launching the app).
        We swallow that specific race harmlessly since the underlying thread
        is a daemon thread that will exit with the process regardless.
        """
        if self._listener:
            try:
                self._listener.stop()
            except AttributeError as e:
                logger.debug("Listener stop race (harmless, thread is a daemon): %s", e)
            except Exception as e:
                logger.warning("Error stopping shortcut listener: %s", e)
            finally:
                self._listener = None
        self._running = False
        self._pressed_keys.clear()
        logger.info("Shortcut listener stopped")

    def _on_press(self, key) -> None:
        """Handle key press event."""
        try:
            with self._lock:
                # Get the character representation
                key_name = self._get_key_name(key)
                self._pressed_keys.add(key_name)

                # Check if current pressed keys match any registered shortcut
                self._check_shortcuts()
        except Exception as e:
            logger.debug("Error in key press handler: %s", e)

    def _on_release(self, key) -> None:
        """Handle key release event."""
        try:
            with self._lock:
                key_name = self._get_key_name(key)
                self._pressed_keys.discard(key_name)
        except Exception as e:
            logger.debug("Error in key release handler: %s", e)

    def _get_key_name(self, key) -> str:
        """Convert pynput key object to string representation."""
        try:
            # Regular character
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            # Function keys, arrows, etc.
            if hasattr(key, 'name'):
                return key.name.lower()
        except Exception:
            pass
        return str(key).lower().strip("<>")

    def _check_shortcuts(self) -> None:
        """Check if any registered shortcut matches currently pressed keys."""
        for shortcut, callbacks in self._shortcuts.items():
            if self._matches_shortcut(shortcut):
                for callback in callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error("Error in shortcut callback: %s", e)

    def _matches_shortcut(self, shortcut: Shortcut) -> bool:
        """Check if a shortcut's modifiers and key are currently pressed."""
        # Check if main key is pressed
        if shortcut.key not in self._pressed_keys:
            return False

        # Check modifiers.
        #
        # NOTE: pynput's X11 backend reports the *left* variant of ctrl/alt/shift
        # using the bare name ("ctrl", "alt", "shift") rather than an "_l" suffixed
        # name — only the *right* variant gets an explicit "_r" suffix (e.g. "ctrl_r").
        # The bare names must therefore be included alongside the "_l"/"_r" forms,
        # otherwise the far more common left-hand modifier keys never match and
        # every default shortcut (Ctrl+Super+...) silently fails to trigger.
        modifier_map = {
            "ctrl": {"ctrl", "ctrl_l", "ctrl_r"},
            "shift": {"shift", "shift_l", "shift_r"},
            "alt": {"alt", "alt_l", "alt_r", "alt_gr"},
            "super": {"cmd", "cmd_l", "cmd_r"},  # pynput reuses the macOS "cmd" name for the Super/Windows key
        }

        for modifier in shortcut.modifiers:
            keys_for_mod = modifier_map.get(modifier, {modifier})
            if not any(k in self._pressed_keys for k in keys_for_mod):
                return False

        return True

    @property
    def is_running(self) -> bool:
        """Check if listener is active."""
        return self._running
