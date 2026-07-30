"""
Hardware abstraction layer for USB HID device communication.

Follows the Dependency Inversion Principle by providing abstract interfaces
for device communication, allowing different monitor implementations.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class HIDReport(ABC):
    """Abstract base for HID report structures. Allows customization per monitor."""

    @property
    @abstractmethod
    def bytes(self) -> bytes:
        """Return the complete HID report as bytes."""
        pass


class HIDDeviceError(Exception):
    """Base exception for HID device communication errors."""
    pass


class HIDDeviceNotFoundError(HIDDeviceError):
    """Raised when the target HID device cannot be found."""
    pass


class HIDDevicePermissionError(HIDDeviceError):
    """Raised when insufficient permissions to access HID device."""
    pass


class IHIDDevice(ABC):
    """
    Abstract interface for HID device communication.
    
    Implementations must handle platform-specific HID communication.
    This allows swapping backends (hidapi, python-evdev, etc).
    """

    @abstractmethod
    def open(self) -> None:
        """Open the HID device. May raise HIDDeviceNotFoundError."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the HID device gracefully."""
        pass

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Check if device is currently open."""
        pass

    @abstractmethod
    def write(self, data: bytes) -> int:
        """
        Write data to the device.
        
        Returns:
            Number of bytes written.
        """
        pass

    @abstractmethod
    def read(self, length: int, timeout_ms: int = 200) -> Optional[bytes]:
        """
        Read data from the device.
        
        Args:
            length: Maximum bytes to read
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Bytes read, or None on timeout.
        """
        pass


class HIDAPIDevice(IHIDDevice):
    """
    Concrete HID device using the hidapi library.
    
    Supports most Linux HID devices without privileged access (when proper udev rules exist).
    """

    def __init__(self, vendor_id: int, product_id: int, interface: int = 0):
        """
        Initialize HID device wrapper.
        
        Args:
            vendor_id: USB vendor ID
            product_id: USB product ID
            interface: HID interface number (default 0)
        """
        try:
            import hid
            self._hid = hid
        except ImportError:
            raise ImportError("hidapi not installed. Run: pip install hid")

        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface = interface
        self._dev = None

    def open(self) -> None:
        """Open the HID device. Raises HIDDeviceNotFoundError if not found."""
        devices = self._hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            raise HIDDeviceNotFoundError(
                f"Device not found (VID=0x{self.vendor_id:04x} PID=0x{self.product_id:04x}). "
                "Check USB connection and udev rules."
            )

        # Prefer interface match, fall back to first device
        target = next(
            (d for d in devices if d.get('interface_number') == self.interface),
            devices[0]
        )

        self._dev = self._hid.device()
        try:
            self._dev.open_path(target['path'])
            self._dev.set_nonblocking(True)
            logger.info("Opened HID device: %s", target['path'])
        except Exception as e:
            raise HIDDevicePermissionError(
                f"Failed to open device: {e}. Check udev rules or run with sudo."
            )

    def close(self) -> None:
        """Close the HID device."""
        if self._dev:
            try:
                self._dev.close()
            except Exception as e:
                logger.warning("Error closing device: %s", e)
            finally:
                self._dev = None

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    def write(self, data: bytes) -> int:
        """Write data to HID device."""
        if not self._dev:
            raise HIDDeviceError("Device not open")
        try:
            return self._dev.write(list(data))
        except Exception as e:
            raise HIDDeviceError(f"Write failed: {e}")

    def read(self, length: int, timeout_ms: int = 200) -> Optional[bytes]:
        """Read data from HID device with timeout."""
        if not self._dev:
            raise HIDDeviceError("Device not open")

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            try:
                data = self._dev.read(length)
                if data:
                    return bytes(data)
            except Exception as e:
                logger.debug("Read error: %s", e)
            time.sleep(0.01)

        return None
