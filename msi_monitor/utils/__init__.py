"""
Utility functions and helpers.
"""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def get_data_dir(app_name: str = "monicon") -> Path:
    """
    Get XDG data directory for application.
    
    Returns:
        Path to ~/.local/share/{app_name}
    """
    data_dir = Path.home() / ".local" / "share" / app_name
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir(app_name: str = "monicon") -> Path:
    """
    Get XDG config directory for application.
    
    Returns:
        Path to ~/.config/{app_name}
    """
    config_dir = Path.home() / ".config" / app_name
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def find_monitor_modules() -> List[Path]:
    """
    Find all monitor definition modules.
    
    Looks in the monitors/ directory for Python modules.
    Returns:
        List of Path objects for monitor modules.
    """
    monitors_dir = Path(__file__).parent.parent / "monitors"
    return sorted(monitors_dir.glob("*.py"))
