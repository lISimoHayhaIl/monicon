# Developer Guide for Monicon

This guide is for developers who want to contribute to Monicon or extend it with support for new monitors.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Setting Up Development Environment](#setting-up-development-environment)
4. [Contributing Code](#contributing-code)
5. [Adding Monitor Support](#adding-monitor-support)
6. [Testing](#testing)
7. [Building Packages](#building-packages)

## Architecture Overview

Monicon follows **SOLID principles** for maintainability and extensibility:

### Single Responsibility Principle (SRP)
Each module has one reason to change:
- `core/` — Hardware abstraction and monitor interfaces
- `config/` — Configuration I/O and persistence
- `shortcuts/` — Keyboard event capture
- `gui/` — User interface components
- `monitors/` — Monitor-specific protocol implementations

### Open/Closed Principle (OCP)
New functionality doesn't require modifying existing code:
- New monitor support: implement `IMonitor` interface
- New GUI elements: extend without changing core
- New shortcuts: register with `ShortcutManager`

### Liskov Substitution Principle (LSP)
All `IMonitor` implementations are interchangeable:
- Controller doesn't care which monitor is used
- Tests can swap in mock implementations

### Interface Segregation Principle (ISP)
Clients depend on small, focused interfaces:
- `IHIDDevice` — only HID operations
- `IMonitor` — only monitor control
- No "fat" interfaces with unused methods

### Dependency Inversion Principle (DIP)
Depend on abstractions, not concrete classes:
- `MonitorController` uses `IMonitor`, not `MSIMPEG341CQR`
- Easy to test with mock objects
- Easy to swap implementations

## Project Structure

```
monicon/
├── msi_monitor/              # Main package
│   ├── __init__.py
│   ├── cli.py                # Command-line interface
│   ├── app.py                # Legacy CLI app controller
│   ├── core/
│   │   ├── __init__.py       # HID device abstraction
│   │   ├── monitor.py        # IMonitor interface
│   │   └── registry.py       # Monitor discovery and registry
│   ├── monitors/
│   │   ├── __init__.py       # Monitor implementations
│   │   └── msi_mpg_341cqr.json  # Monitor definition
│   ├── config/
│   │   └── __init__.py       # Configuration management
│   ├── shortcuts/
│   │   └── __init__.py       # Keyboard shortcut handling
│   ├── gui/
│   │   ├── __init__.py       # Tray icon base
│   │   ├── window.py         # PyQt6 window implementation
│   │   └── app.py            # Complete GUI application
│   └── utils/
│       └── __init__.py       # Utility functions
├── tests/
│   ├── test_core.py          # Core component tests
│   └── ...                   # Additional tests
├── packaging/
│   ├── arch/PKGBUILD         # Arch Linux package
│   ├── fedora/monicon.spec   # Fedora/RHEL package
│   ├── opensuse/monicon.spec # openSUSE package
│   └── debian/               # Debian package files
├── pyproject.toml            # Python project configuration
├── README.md                 # User documentation
├── INSTALL.md                # Installation guide
└── LICENSE                   # GPL-3.0-or-later
```

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/monicon-dev/monicon.git
cd monicon
git checkout feat/refactor-solid-tray-gui
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

### 3. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- `hidapi` — USB HID communication
- `pynput` — Keyboard shortcuts
- `PyQt6` — GUI framework
- `pytest` — Testing framework
- `black` — Code formatter
- `ruff` — Linter

### 4. Install udev Rules (Linux)

```bash
sudo cp 90-msi-monitor.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

## Contributing Code

### Code Style

We use **Black** for formatting and **Ruff** for linting:

```bash
# Format code
black msi_monitor/ tests/

# Check linting
ruff check msi_monitor/ tests/
```

### Commit Messages

Follow conventional commits:

```
feat: add new feature
fix: fix a bug
docs: documentation changes
refactor: code refactoring
test: add or update tests
```

Example:
```
feat: add support for MSI MPG 271CQR monitor

- Implement protocol support for new model
- Add input source definitions
- Add test coverage
```

### Creating a Pull Request

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make changes and commit
3. Push to your fork: `git push origin feat/my-feature`
4. Create PR with description of changes
5. Ensure tests pass and linting is clean

## Adding Monitor Support

### Step 1: Capture Protocol

Use Wireshark to capture USB communication from the Windows MSI software:

```bash
# Enable USB monitoring
sudo modprobe usbmon

# Open Wireshark and capture on usbmon1
# Filter: usb.idVendor == 0x1462 (MSI vendor ID)

# Use MSI Gaming Intelligence to change settings
# Export capture as .pcapng file
```

### Step 2: Analyze Protocol

Create a text file documenting the commands:

```
# MSI MPG XXX Monitor Protocol

Input sources:
- HDMI 1: 5800110
- HDMI 2: 5800120
- DisplayPort: 5800130

Profiles:
- Eco: (command)
- Gaming: (command)

Responses:
- Echo: Replace '8' with 'b'
```

### Step 3: Implement Monitor Class

Create `msi_monitor/monitors/msi_mpg_xxx.py`:

```python
from msi_monitor.core.monitor import IMonitor, MonitorInfo, InputSource, Profile
from msi_monitor.core import HIDAPIDevice

class MSIMPGMonitor(IMonitor):
    """Implementation for MSI MPG XXX monitor."""

    VENDOR_ID = 0x1462
    PRODUCT_ID = 0xABCD  # Your monitor's PID

    def __init__(self):
        self._device = HIDAPIDevice(self.VENDOR_ID, self.PRODUCT_ID)
        self._info = MonitorInfo(
            model_name="MSI MPG XXX",
            vendor_id=self.VENDOR_ID,
            product_id=self.PRODUCT_ID,
            inputs=[
                InputSource("hdmi1", "HDMI 1"),
                InputSource("hdmi2", "HDMI 2"),
                InputSource("dp", "DisplayPort"),
            ],
            profiles=[
                Profile("eco", "Eco"),
                Profile("gaming", "Gaming"),
            ],
        )

    @property
    def info(self) -> MonitorInfo:
        return self._info

    def open(self) -> None:
        self._device.open()

    def close(self) -> None:
        self._device.close()

    @property
    def is_open(self) -> bool:
        return self._device.is_open

    def set_input(self, source_id: str) -> bool:
        # Implement input switching
        pass

    def next_profile(self) -> bool:
        # Implement profile cycling
        pass

    # ... other required methods
```

### Step 4: Create Monitor Definition File

Create `msi_monitor/monitors/msi_mpg_xxx.json`:

```json
{
  "id": "msi_mpg_xxx",
  "name": "MSI MPG XXX",
  "vendor_id": "0x1462",
  "product_id": "0xABCD",
  "inputs": [
    {
      "id": "hdmi1",
      "name": "HDMI 1"
    },
    {
      "id": "dp",
      "name": "DisplayPort"
    }
  ],
  "profiles": [
    {
      "id": "eco",
      "name": "Eco"
    }
  ]
}
```

### Step 5: Write Tests

Add tests in `tests/test_monitors.py`:

```python
def test_msi_mpg_xxx_input_switching():
    """Test input switching for MSI MPG XXX."""
    monitor = MSIMPGMonitor()
    # Mock the HID device
    monitor._device = Mock()
    monitor.open()
    
    assert monitor.set_input("dp") is True
    monitor._device.write.assert_called()
```

### Step 6: Submit Pull Request

Include:
- Monitor implementation
- Protocol definition file
- Tests
- Wireshark capture file
- Documentation of any new features

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=msi_monitor tests/
```

### Test Coverage

Aim for >80% coverage on new code:

```bash
pytest --cov=msi_monitor --cov-report=html
```

View coverage report: `htmlcov/index.html`

### Mock Objects

For testing without hardware:

```python
from unittest.mock import Mock, patch

def test_without_monitor():
    """Test GUI without physical monitor."""
    with patch('msi_monitor.monitors.MSIMPEG341CQR'):
        app = MonitorApplicationGUI()
        # ... test logic
```

## Building Packages

### Arch Linux

```bash
cd packaging/arch
makepkg -si
```

### Fedora

```bash
cd packaging/fedora
rpm -ba monicon.spec
```

### openSUSE

```bash
cd packaging/opensuse
osc build
```

### Debian

```bash
cd packaging/debian
debuild -us -uc
sudo dpkg -i ../monicon_*.deb
```

## Common Issues

### PyQt6 Import Error

```bash
pip install --upgrade PyQt6
```

### pynput Keyboard Not Working

```bash
pip install --upgrade pynput
# On some systems, may need additional X11 libraries
```

### HID Device Permissions

```bash
# Ensure udev rules are installed
sudo cp 90-msi-monitor.rules /etc/udev/rules.d/
sudo udevadm control --reload
```

## Resources

- **Protocol Analysis**: Wireshark capture files (`.pcapng`)
- **Python HID**: https://github.com/pyusb/hidapi
- **PyQt6 Docs**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **pynput Docs**: https://pynput.readthedocs.io/

## Getting Help

- **Issues & Discussions**: https://github.com/monicon-dev/monicon
- **Documentation**: README.md and INSTALL.md
- **Code Comments**: Inline documentation explains complex logic
