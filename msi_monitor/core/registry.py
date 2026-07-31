"""
Monitor registry and discovery system.

Allows loading monitor definitions from separate folders for user extensibility
and community contributions.

Folder structure:
  ~/.local/share/monicon/monitors/
    msi_mpg_341cqr.yaml
    msi_mpg_251cqr.yaml
    asus_custom.yaml
    ...
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from msi_monitor.core.monitor import IMonitor, MonitorInfo, InputSource, Profile
from msi_monitor.utils import get_data_dir

logger = logging.getLogger(__name__)


class MonitorRegistry:
    """
    Registry for available monitor definitions.
    
    Loads monitor info from:
    1. Built-in monitors (msi_monitor/monitors/)
    2. User monitors (~/.local/share/monicon/monitors/)
    
    This allows users to add support for their own monitors without modifying source.
    """

    def __init__(self):
        """Initialize the monitor registry."""
        self._monitors: Dict[str, MonitorInfo] = {}
        self._load_builtin_monitors()
        self._load_user_monitors()

    def _load_builtin_monitors(self) -> None:
        """
        Load built-in monitor definitions from msi_monitor/monitors/*.json.

        Per requirement #11, monitor metadata lives in its own JSON files
        (not hardcoded in Python) so contributors can add support for new
        monitors purely by dropping a new JSON file in this folder and
        submitting a PR — no core code changes required.
        """
        builtin_dir = Path(__file__).resolve().parent.parent / "monitors"
        if not builtin_dir.exists():
            logger.warning("Built-in monitors directory not found: %s", builtin_dir)
            return

        for json_file in sorted(builtin_dir.glob("*.json")):
            try:
                self._load_monitor_file(json_file)
            except Exception as e:
                logger.error("Failed to load built-in monitor from %s: %s", json_file, e)

    def _load_user_monitors(self) -> None:
        """Load user-defined monitor definitions from ~/.local/share/monicon/monitors/."""
        user_monitors_dir = get_data_dir("monicon") / "monitors"
        user_monitors_dir.mkdir(parents=True, exist_ok=True)

        if not user_monitors_dir.exists():
            logger.debug("User monitors directory not found: %s", user_monitors_dir)
            return

        for yaml_file in user_monitors_dir.glob("*.yaml"):
            try:
                self._load_monitor_file(yaml_file)
            except Exception as e:
                logger.error("Failed to load monitor from %s: %s", yaml_file, e)

        for json_file in user_monitors_dir.glob("*.json"):
            try:
                self._load_monitor_file(json_file)
            except Exception as e:
                logger.error("Failed to load monitor from %s: %s", json_file, e)

    def _load_monitor_file(self, file_path: Path) -> None:
        """Load a single monitor definition file (YAML or JSON)."""
        try:
            if file_path.suffix == ".json":
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self._parse_monitor_data(data, file_path)
            elif file_path.suffix == ".yaml" or file_path.suffix == ".yml":
                try:
                    import yaml
                    with open(file_path, 'r') as f:
                        data = yaml.safe_load(f)
                    self._parse_monitor_data(data, file_path)
                except ImportError:
                    logger.warning("pyyaml not installed, skipping YAML file: %s", file_path)
        except Exception as e:
            logger.error("Error loading monitor definition %s: %s", file_path, e)

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        """
        Coerce a USB id field to int, accepting either a JSON number or a
        "0x1462"-style hex string (auto-detected via base 0).
        """
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)  # base=0 auto-detects "0x..." vs plain decimal
        return default

    def _parse_monitor_data(self, data: Dict, file_path: Path) -> None:
        """Parse monitor definition from data dict."""
        model_id = data.get('id', file_path.stem)
        model_name = data.get('name', 'Unknown Monitor')
        vendor_id = self._to_int(data.get('vendor_id'))
        product_id = self._to_int(data.get('product_id'))
        description = data.get('description', '')

        # Parse inputs
        inputs = []
        for inp in data.get('inputs', []):
            inputs.append(InputSource(
                id=inp['id'],
                display_name=inp.get('name', inp['id']),
                description=inp.get('description', '')
            ))

        # Parse profiles
        profiles = []
        for prof in data.get('profiles', []):
            profiles.append(Profile(
                id=prof['id'],
                display_name=prof.get('name', prof['id']),
                description=prof.get('description', '')
            ))

        monitor_info = MonitorInfo(
            model_name=model_name,
            vendor_id=vendor_id,
            product_id=product_id,
            description=description,
            inputs=inputs,
            profiles=profiles,
        )

        self.register(model_id, monitor_info)
        logger.info("Loaded monitor definition: %s (%s)", model_name, file_path)

    def register(self, model_id: str, info: MonitorInfo) -> None:
        """Register a monitor definition."""
        self._monitors[model_id] = info

    def get(self, model_id: str) -> Optional[MonitorInfo]:
        """Get monitor info by ID."""
        return self._monitors.get(model_id)

    def get_by_usb_id(self, vendor_id: int, product_id: int) -> Optional[MonitorInfo]:
        """Find monitor by USB vendor ID and product ID."""
        for info in self._monitors.values():
            if info.vendor_id == vendor_id and info.product_id == product_id:
                return info
        return None

    def list_all(self) -> List[MonitorInfo]:
        """List all available monitors."""
        return list(self._monitors.values())

    def list_ids(self) -> List[str]:
        """List all monitor IDs."""
        return list(self._monitors.keys())
