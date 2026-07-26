"""
MSI Monitor HID Device Communication
VID: 0x1462, PID: 0x3fa4 (MPG 341CQR QD-OLED X36)

Protocol: ASCII text commands over HID Interrupt/Control transfers
Format:   [ReportID=0x01][ASCII_CMD][0x0D terminator][0x00 padding to 64 bytes]
"""

import hid
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VENDOR_ID  = 0x1462
PRODUCT_ID = 0x3fa4

# HID Interface 0 — settings/input/profile control
# EP2 OUT (commands TO monitor), EP1 IN (responses FROM monitor)
INTERFACE  = 0
REPORT_ID  = 0x01
MSG_LEN    = 64
TERMINATOR = b'\x0d'

# Input source values (byte[5] - 0x30 = decimal value)
INPUT_SOURCES = {
    "hdmi1": b'5800110',  # val=1
    "hdmi2": b'5800120',  # val=2
    "dp":    b'5800130',  # val=3
    "usb-c": b'5800140',  # val=4
}

# Known commands from capture analysis
CMD_QUERY_INPUT   = b'5800140'  # Query current input
CMD_QUERY_STATUS  = b'5800150'  # Query status
CMD_NEXT_PROFILE  = b'5800190'  # Cycle to next picture profile
CMD_HEARTBEAT_A   = b'6800;30'  # Sent periodically by MSI software
CMD_HEARTBEAT_B   = b'5800110'  # Sent periodically by MSI software


def _build_report(cmd: bytes) -> bytes:
    """Build a 64-byte HID report: [ReportID][cmd][0x0D][0x00 padding]."""
    payload = bytes([REPORT_ID]) + cmd + TERMINATOR
    return payload + b'\x00' * (MSG_LEN - len(payload))


def _parse_response(data: bytes) -> Optional[str]:
    """Parse a HID response report into an ASCII string (up to 0x0D)."""
    if not data or data[0] != REPORT_ID:
        return None
    body = bytes(data[1:])
    end = body.find(b'\x0d')
    if end >= 0:
        body = body[:end]
    try:
        return body.rstrip(b'\x00').decode('ascii')
    except UnicodeDecodeError:
        return body.hex()


class MSIMonitor:
    """
    Low-level interface to the MSI MPG 341CQR over HID.

    Usage:
        with MSIMonitor() as mon:
            mon.set_input("dp")
    """

    def __init__(self, vendor_id: int = VENDOR_ID, product_id: int = PRODUCT_ID):
        self.vendor_id  = vendor_id
        self.product_id = product_id
        self._dev: Optional[hid.device] = None

    # ------------------------------------------------------------------ #
    #  Context manager                                                     #
    # ------------------------------------------------------------------ #

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------ #
    #  Connection                                                          #
    # ------------------------------------------------------------------ #

    def open(self) -> None:
        """Open the HID device. Raises RuntimeError if not found."""
        devices = hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            raise RuntimeError(
                f"MSI monitor not found (VID=0x{self.vendor_id:04x} "
                f"PID=0x{self.product_id:04x}). "
                "Is the USB cable connected? Check udev rules."
            )

        # Interface 0 is the settings/control interface
        target = next(
            (d for d in devices if d.get('interface_number') == INTERFACE),
            devices[0]
        )

        self._dev = hid.device()
        self._dev.open_path(target['path'])
        self._dev.set_nonblocking(True)
        logger.debug("Opened %s", target['path'])

    def close(self) -> None:
        if self._dev:
            self._dev.close()
            self._dev = None
            logger.debug("Device closed")

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    # ------------------------------------------------------------------ #
    #  Low-level send / receive                                            #
    # ------------------------------------------------------------------ #

    def _send(self, cmd: bytes) -> None:
        """Send a command report to the monitor."""
        if not self._dev:
            raise RuntimeError("Device not open")
        report = _build_report(cmd)
        logger.debug("TX: %s", cmd.decode('ascii', errors='replace'))
        # hidapi write() prepends the report ID automatically on some
        # platforms; we include it explicitly and use raw write.
        self._dev.write(list(report))

    def _recv(self, timeout_ms: int = 200) -> Optional[str]:
        """Read one response report from the monitor."""
        if not self._dev:
            raise RuntimeError("Device not open")
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            data = self._dev.read(MSG_LEN)
            if data:
                response = _parse_response(data)
                logger.debug("RX: %s", response)
                return response
            time.sleep(0.01)
        return None

    def send_command(self, cmd: bytes, wait_response: bool = True) -> Optional[str]:
        """
        Send a command and optionally read the response.
        Returns the decoded ASCII response, or None on timeout.
        """
        self._send(cmd)
        if wait_response:
            return self._recv()
        return None

    # ------------------------------------------------------------------ #
    #  High-level actions                                                  #
    # ------------------------------------------------------------------ #

    def get_current_input(self) -> Optional[str]:
        """
        Query the current input source.
        Returns a raw response string (needs more capture data to decode fully).
        """
        return self.send_command(CMD_QUERY_INPUT)

    def set_input(self, source: str) -> bool:
        """
        Switch to a specific input source.

        Args:
            source: one of "hdmi1", "hdmi2", "dp", "usb-c"

        Returns:
            True if command was sent successfully, False otherwise.
        """
        source = source.lower().strip()
        cmd = INPUT_SOURCES.get(source)
        if cmd is None:
            raise ValueError(
                f"Unknown input source '{source}'. "
                f"Valid options: {list(INPUT_SOURCES.keys())}"
            )
        logger.info("Switching input to: %s", source)
        response = self.send_command(cmd)
        logger.debug("set_input response: %s", response)
        return True

    def next_profile(self) -> Optional[str]:
        """Cycle to the next picture profile (Eco → FPS → Racing → ...)."""
        logger.info("Cycling to next picture profile")
        return self.send_command(CMD_NEXT_PROFILE)

    def query_status(self) -> Optional[str]:
        """Query general monitor status."""
        return self.send_command(CMD_QUERY_STATUS)
