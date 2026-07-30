"""
Monitor implementations for specific monitor models.

Each monitor model implements the IMonitor interface with model-specific protocol handling.
"""

import logging
from typing import Optional

from msi_monitor.core import HIDAPIDevice, HIDDeviceError
from msi_monitor.core.monitor import IMonitor, MonitorInfo, InputSource, Profile

logger = logging.getLogger(__name__)

# ==============================================================================
#  MSI MPG 341 CQR QD-OLED X36
# ==============================================================================

class MSIMPEG341CQR(IMonitor):
    """
    Control interface for MSI MPG 341CQR QD-OLED X36 monitor.

    Protocol: ASCII text-based HID commands
    Format:   [ReportID=0x01][ASCII_CMD][0x0D terminator][0x00 padding to 64 bytes]
    
    Reverse-engineered via Wireshark capture of Windows MSI Gaming Intelligence software.
    """

    VENDOR_ID = 0x1462
    PRODUCT_ID = 0x3fa4
    INTERFACE = 0
    REPORT_ID = 0x01
    REPORT_LEN = 64
    TERMINATOR = b'\x0d'

    # Input source commands (byte[5] encodes the source value)
    _INPUTS = {
        "hdmi1": b'5800110',
        "hdmi2": b'5800120',
        "dp": b'5800130',
        "usb_c": b'5800140',
    }

    # Protocol commands
    _CMD_QUERY_INPUT = b'5800140'
    _CMD_QUERY_STATUS = b'5800150'
    _CMD_NEXT_PROFILE = b'5800190'

    def __init__(self):
        """Initialize the monitor interface."""
        self._device = HIDAPIDevice(self.VENDOR_ID, self.PRODUCT_ID, self.INTERFACE)
        self._info = MonitorInfo(
            model_name="MSI MPG 341CQR QD-OLED X36",
            vendor_id=self.VENDOR_ID,
            product_id=self.PRODUCT_ID,
            description="Ultra-wide QD-OLED gaming monitor",
            inputs=[
                InputSource("hdmi1", "HDMI 1"),
                InputSource("hdmi2", "HDMI 2"),
                InputSource("dp", "DisplayPort"),
                InputSource("usb_c", "USB-C"),
            ],
            profiles=[
                Profile("eco", "Eco"),
                Profile("fps", "FPS"),
                Profile("racing", "Racing"),
                Profile("rpg", "RPG"),
                Profile("srgb", "sRGB"),
                Profile("movie", "Movie"),
            ],
        )
        self._current_input = None
        self._current_profile = None

    @property
    def info(self) -> MonitorInfo:
        return self._info

    def open(self) -> None:
        """Connect to the monitor."""
        self._device.open()

    def close(self) -> None:
        """Disconnect from the monitor."""
        self._device.close()

    @property
    def is_open(self) -> bool:
        return self._device.is_open

    # ========================================================================
    #  Protocol helpers (private)
    # ========================================================================

    def _build_report(self, cmd: bytes) -> bytes:
        """Build a 64-byte HID report with proper formatting."""
        payload = bytes([self.REPORT_ID]) + cmd + self.TERMINATOR
        return payload + b'\x00' * (self.REPORT_LEN - len(payload))

    def _parse_response(self, data: bytes) -> Optional[str]:
        """Parse ASCII response from HID report."""
        if not data or data[0] != self.REPORT_ID:
            return None
        body = bytes(data[1:])
        end = body.find(b'\x0d')
        if end >= 0:
            body = body[:end]
        try:
            return body.rstrip(b'\x00').decode('ascii')
        except (UnicodeDecodeError, AttributeError):
            logger.debug("Could not decode response: %s", body.hex())
            return body.hex()

    def _send_command(self, cmd: bytes, wait_response: bool = True) -> Optional[str]:
        """Send a command and optionally wait for response."""
        if not self.is_open:
            raise HIDDeviceError("Monitor not open")

        try:
            report = self._build_report(cmd)
            self._device.write(report)
            logger.debug("TX: %s", cmd.decode('ascii', errors='replace'))

            if wait_response:
                response_bytes = self._device.read(self.REPORT_LEN, timeout_ms=200)
                if response_bytes:
                    response = self._parse_response(response_bytes)
                    logger.debug("RX: %s", response)
                    return response
                else:
                    logger.warning("No response from monitor (timeout)")
            return None
        except HIDDeviceError as e:
            logger.error("Device error: %s", e)
            raise

    # ========================================================================
    #  Input source control
    # ========================================================================

    def get_current_input(self) -> Optional[str]:
        """Query current input source from monitor."""
        try:
            response = self._send_command(self._CMD_QUERY_INPUT)
            # TODO: Parse response to determine actual input (needs more capture data)
            return self._current_input
        except HIDDeviceError:
            return None

    def set_input(self, source_id: str) -> bool:
        """Set the input source."""
        source_id = source_id.lower().strip()
        if source_id not in self._INPUTS:
            logger.error(
                "Unknown input source '%s'. Valid: %s",
                source_id,
                list(self._INPUTS.keys())
            )
            return False

        try:
            cmd = self._INPUTS[source_id]
            response = self._send_command(cmd)
            self._current_input = source_id
            logger.info("Input switched to: %s", source_id)
            return True
        except HIDDeviceError as e:
            logger.error("Failed to set input: %s", e)
            return False

    # ========================================================================
    #  Profile control
    # ========================================================================

    def get_current_profile(self) -> Optional[str]:
        """Get the current profile ID."""
        # TODO: Implement profile query via protocol analysis
        return self._current_profile

    def set_profile(self, profile_id: str) -> bool:
        """Set a specific profile."""
        # TODO: Implement profile setting via protocol analysis
        logger.warning("Profile setting not yet implemented for this monitor")
        return False

    def next_profile(self) -> bool:
        """Cycle to the next profile."""
        try:
            response = self._send_command(self._CMD_NEXT_PROFILE)
            logger.info("Cycled to next profile")
            return True
        except HIDDeviceError as e:
            logger.error("Failed to cycle profile: %s", e)
            return False

    def supports_feature(self, feature: str) -> bool:
        """Check if monitor supports a feature."""
        feature_map = {
            "input_switching": True,
            "profile_cycling": True,
            "profile_selection": False,  # Not yet reverse-engineered
            "status_query": True,
        }
        return feature_map.get(feature, False)
