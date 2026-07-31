"""
Monitor implementations for specific monitor models.

Each monitor model implements the IMonitor interface with model-specific protocol handling.
"""

import logging
from typing import Dict, Optional, Type

from msi_monitor.core import HIDAPIDevice, HIDDeviceError
from msi_monitor.core.monitor import IMonitor, MonitorInfo, InputSource, Profile
from msi_monitor.core.registry import MonitorRegistry

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

    Metadata (model name, inputs, profiles, USB ids) is NOT hardcoded here — it is
    loaded from msi_monitor/monitors/msi_mpg_341cqr.json via MonitorRegistry. This
    keeps hardware description and protocol implementation independent, per the
    "monitor info should be independent of the application" requirement: a
    contributor can update supported inputs/profiles by editing the JSON file alone.
    """

    REGISTRY_ID = "msi_mpg_341cqr"
    INTERFACE = 0
    REPORT_ID = 0x01
    REPORT_LEN = 64
    TERMINATOR = b'\x0d'

    # Input source commands (byte[5] encodes the source value).
    # These are protocol-specific and therefore stay in code, not JSON.
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

    def __init__(self, info: Optional[MonitorInfo] = None):
        """
        Initialize the monitor interface.

        Args:
            info: MonitorInfo to use (normally supplied by MonitorRegistry, which
                  loads it from msi_mpg_341cqr.json). Falls back to a minimal
                  built-in definition if the registry entry is unavailable, so the
                  class still works standalone (e.g. in unit tests).
        """
        if info is None:
            registry = MonitorRegistry()
            info = registry.get(self.REGISTRY_ID)
        if info is None:
            # Last-resort fallback so this class never crashes if the JSON file
            # is missing/corrupt; keeps the app usable in a degraded state.
            logger.warning(
                "Monitor definition '%s' not found in registry; using built-in fallback",
                self.REGISTRY_ID,
            )
            info = MonitorInfo(
                model_name="MSI MPG 341CQR QD-OLED X36",
                vendor_id=0x1462,
                product_id=0x3fa4,
                description="Ultra-wide QD-OLED gaming monitor",
                inputs=[InputSource(k, k.upper()) for k in self._INPUTS],
                profiles=[Profile("eco", "Eco")],
            )

        self._info = info
        self._device = HIDAPIDevice(info.vendor_id, info.product_id, self.INTERFACE)
        self._current_input = None
        self._current_profile = None
        # Profile order used to compute how many "next profile" cycles are
        # needed to reach a specific target (the protocol only exposes cycling,
        # not direct selection — see set_profile()).
        self._profile_order = [p.id for p in self._info.profiles]

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
        """
        Get the last input source we successfully commanded the monitor to use.

        IMPORTANT: the monitor's HID protocol has no working "query active
        input" command — sending 5800140 always returns the identical fixed
        response regardless of which input is actually selected (verified by
        querying before/after switching inputs on real hardware). So this
        cannot read the monitor's true hardware state; it only returns our
        last known *commanded* value (None if we've never successfully sent a
        set_input() in this session, or if the input was changed via the
        physical OSD/remote instead of this app).
        """
        try:
            self._send_command(self._CMD_QUERY_INPUT)  # diagnostic ping only; response is not decodable
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
        return self._current_profile

    def set_profile(self, profile_id: str) -> bool:
        """
        Set a specific profile.

        The reverse-engineered protocol only exposes a "next profile" command
        (there is no direct "set profile N" command in the capture). We emulate
        direct selection by cycling forward the minimum number of steps needed
        to reach the target profile from the last known one. This is best-effort:
        if the monitor's actual current profile drifts from our tracked state
        (e.g. changed via the physical OSD), the first selection may land on the
        wrong profile; subsequent selections self-correct once `next_profile()`
        keeps our tracked index in sync.
        """
        profile_id = profile_id.lower().strip()
        if profile_id not in self._profile_order:
            logger.error(
                "Unknown profile '%s'. Valid: %s", profile_id, self._profile_order
            )
            return False

        if self._current_profile is None:
            # Unknown starting point: assume the monitor is at the first profile.
            self._current_profile = self._profile_order[0]

        current_index = self._profile_order.index(self._current_profile)
        target_index = self._profile_order.index(profile_id)
        steps = (target_index - current_index) % len(self._profile_order)

        if steps == 0:
            logger.debug("Profile '%s' already selected", profile_id)
            return True

        for _ in range(steps):
            if not self.next_profile():
                return False
        return True

    def next_profile(self) -> bool:
        """Cycle to the next profile."""
        try:
            response = self._send_command(self._CMD_NEXT_PROFILE)
            if self._profile_order:
                if self._current_profile is None:
                    self._current_profile = self._profile_order[0]
                else:
                    idx = self._profile_order.index(self._current_profile)
                    self._current_profile = self._profile_order[(idx + 1) % len(self._profile_order)]
            logger.info("Cycled to next profile (now: %s)", self._current_profile)
            return True
        except HIDDeviceError as e:
            logger.error("Failed to cycle profile: %s", e)
            return False

    def supports_feature(self, feature: str) -> bool:
        """Check if monitor supports a feature."""
        feature_map = {
            "input_switching": True,
            "profile_cycling": True,
            "profile_selection": True,  # Emulated via cycling, see set_profile()
            "status_query": True,
        }
        return feature_map.get(feature, False)


# ==============================================================================
#  Monitor factory — maps registry ids to concrete IMonitor implementations
# ==============================================================================

# Only monitors with a reverse-engineered protocol have a concrete class here.
# Community-contributed monitor JSON files (req #11) are still readable via the
# registry for display purposes even before someone implements their protocol.
_MONITOR_CLASSES: Dict[str, Type[IMonitor]] = {
    "msi_mpg_341cqr": MSIMPEG341CQR,
}


def create_monitor(model_id: str, registry: Optional[MonitorRegistry] = None) -> Optional[IMonitor]:
    """
    Instantiate the IMonitor implementation for a given registry model id.

    Args:
        model_id: Registry id, e.g. "msi_mpg_341cqr" (see msi_monitor/monitors/*.json)
        registry: Optional pre-built MonitorRegistry (avoids re-scanning disk)

    Returns:
        An IMonitor instance, or None if no protocol implementation exists yet
        for that model (e.g. a user just added metadata but no control code).
    """
    registry = registry or MonitorRegistry()
    info = registry.get(model_id)
    monitor_cls = _MONITOR_CLASSES.get(model_id)

    if monitor_cls is None:
        logger.warning(
            "No protocol implementation registered for monitor '%s'. "
            "Its metadata can be displayed but commands cannot be sent yet.",
            model_id,
        )
        return None

    return monitor_cls(info) if info is not None else monitor_cls()

