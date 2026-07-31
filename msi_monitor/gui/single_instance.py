"""
Single-instance enforcement for the Monicon GUI.

Why this exists: without it, launching Monicon a second time (e.g. via the
desktop launcher, or a leftover process from a previous session) silently
starts a second, independent process. hidapi does not exclusively lock the
HID device, so both processes can open it — but only ONE of the two visible
windows/tray icons is actually "the one the user is looking at" at any given
moment. Clicking "Switch" in the second, freshly-launched window may appear
to do nothing if the user is actually still looking at (or their desktop
session focuses) the first instance, or vice versa. This also means bugfixes
loaded into a new process are invisible if an old process from before the
fix is still silently running in the tray.

Uses PyQt6's QLocalServer/QLocalSocket (already a PyQt6 dependency, so this
adds no new third-party libraries) to implement a simple local IPC lock:
the first instance binds a named local socket; any later instance detects
the existing bind, asks it to raise its window, and exits.
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SingleInstanceGuard:
    """Ensures only one instance of the application runs at a time."""

    def __init__(self, key: str):
        """
        Args:
            key: Unique name for the local socket (e.g. "monicon"). Scoped
                 per-user automatically by QLocalServer on Linux.
        """
        self._key = key
        self._server = None  # QLocalServer, held only by the primary instance
        self._client_socket = None

    def try_acquire(self, on_second_instance: Optional[Callable[[], None]] = None) -> bool:
        """
        Attempt to become the primary instance.

        Returns:
            True if this process is now the (only) primary instance and
            should proceed with startup. False if another instance is
            already running — in that case, `on_second_instance` (if given)
            is invoked in the *existing* primary instance to bring its
            window to front, and the caller should exit without starting a
            second copy of the app.
        """
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket

        # First, try connecting as a *client* to see if a primary instance
        # already owns this socket name.
        socket = QLocalSocket()
        socket.connectToServer(self._key)
        if socket.waitForConnected(200):
            # A primary instance is alive; ask it to raise its window, then
            # this (second) process should exit.
            socket.write(b"show\n")
            socket.waitForBytesWritten(200)
            socket.disconnectFromServer()
            logger.info("Another Monicon instance is already running.")
            return False

        # No primary instance responded — become the primary. Remove any
        # stale socket file left behind by a crashed previous instance
        # before (re)listening, otherwise QLocalServer::listen() fails.
        QLocalServer.removeServer(self._key)

        self._server = QLocalServer()
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)

        if on_second_instance is not None:
            def _handle_new_connection():
                conn = self._server.nextPendingConnection()
                if conn is not None:
                    conn.readyRead.connect(lambda: (conn.readAll(), on_second_instance()))
                    conn.disconnected.connect(conn.deleteLater)

            self._server.newConnection.connect(_handle_new_connection)

        if not self._server.listen(self._key):
            # Extremely unlikely race (another process grabbed it between our
            # check and listen()) — fail safe by treating this as "already
            # running" rather than risking two primaries.
            logger.warning(
                "Could not bind single-instance socket (%s); assuming another "
                "instance won the race.", self._server.errorString(),
            )
            return False

        return True

    def release(self) -> None:
        """Release the single-instance lock (call on shutdown)."""
        if self._server is not None:
            self._server.close()
            self._server = None
