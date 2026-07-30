"""
Abstract monitor interface following the Interface Segregation Principle.

Defines the contract for all monitor implementations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class InputSource:
    """Represents an input source option."""
    id: str          # Internal identifier (e.g., "dp", "hdmi1")
    display_name: str  # User-friendly name (e.g., "DisplayPort", "HDMI 1")
    description: str = ""


@dataclass
class Profile:
    """Represents a settings profile."""
    id: str          # Internal identifier (e.g., "racing", "srgb")
    display_name: str  # User-friendly name
    description: str = ""


class MonitorInfo:
    """Metadata about a monitor model."""

    def __init__(
        self,
        model_name: str,
        vendor_id: int,
        product_id: int,
        description: str = "",
        inputs: List[InputSource] = None,
        profiles: List[Profile] = None,
    ):
        self.model_name = model_name
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.description = description
        self.inputs = inputs or []
        self.profiles = profiles or []


class IMonitor(ABC):
    """
    Abstract interface for monitor communication and control.

    Implementations handle protocol-specific communication for different monitor models.
    This adheres to the Open/Closed Principle: open for extension, closed for modification.
    """

    @property
    @abstractmethod
    def info(self) -> MonitorInfo:
        """Get monitor metadata and capabilities."""
        pass

    @abstractmethod
    def open(self) -> None:
        """Connect to the monitor device."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Disconnect from the monitor."""
        pass

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Check if connection is active."""
        pass

    @abstractmethod
    def get_current_input(self) -> Optional[str]:
        """Get the current input source ID."""
        pass

    @abstractmethod
    def set_input(self, source_id: str) -> bool:
        """Set the input source."""
        pass

    @abstractmethod
    def get_current_profile(self) -> Optional[str]:
        """Get the current profile ID."""
        pass

    @abstractmethod
    def set_profile(self, profile_id: str) -> bool:
        """Set the profile."""
        pass

    @abstractmethod
    def next_profile(self) -> bool:
        """Cycle to the next profile."""
        pass

    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check if monitor supports a feature (e.g., "profiles", "input_switching")."""
        pass

    # ------------------------------------------------------------------
    # Context manager support (shared by all implementations).
    # Lets callers write `with monitor: ...` instead of manual open()/close(),
    # guaranteeing the HID handle is released even if an exception occurs.
    # ------------------------------------------------------------------
    def __enter__(self) -> "IMonitor":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
