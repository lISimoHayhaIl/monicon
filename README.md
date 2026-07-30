# Monicon — MSI Monitor Control on Linux

**Modern system tray application to control MSI gaming monitors on Linux with global keybindings, input switching, and profile management.**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](LICENSE)

Currently tested on: **MSI MPG 341CQR QD-OLED X36**

## Features

✨ **System Tray Integration**
- Minimizes to system tray (works on all Linux DEs)
- Left-click menu for quick input/profile access
- Global keyboard shortcuts (Ctrl+Super+1/2/P by default)
- Confirm on quit, close button minimizes to tray

✨ **Input Switching & Profiles**
- Switch between HDMI1, HDMI2, DisplayPort instantly
- Cycle through picture profiles (Eco, FPS, Racing, RPG, sRGB, Movie, …)
- Custom names for inputs and profiles (rename to your preference)

✨ **Modern Architecture**
- Follows SOLID principles for maintainability
- Pluggable monitor support (easy to add new monitor models)
- Open-source, free, no copyrighted/paid dependencies
- Clean separation: monitor protocols ↔ config ↔ GUI

✨ **Cross-Platform & Cross-Desktop**
- Works on any Linux distribution (Arch, Fedora, openSUSE, Debian, Ubuntu, etc.)
- Compatible with all desktop environments (GNOME, KDE, XFCE, i3, etc.)
- Uses standard XDG directories for configuration

## Installation

### Prerequisites

**System Dependencies:**
```bash
# Arch / CachyOS
sudo pacman -S hidapi libusb python-pyqt6

# Fedora
sudo dnf install hidapi libusb python3-pyqt6

# openSUSE
sudo zypper install hidapi libusb python3-PyQt6

# Debian / Ubuntu
sudo apt install libhidapi-hidraw0 libusb-1.0-0 python3-pyqt6
```

**udev Rule (required for access without sudo):**
```bash
sudo cp 90-msi-monitor.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger
sudo usermod -aG plugdev $USER
# Log out and back in for group membership to take effect
```

### From Source (Development)

```bash
git clone https://github.com/your-username/monicon
cd monicon
pip install --user -e .
```

### From Package

**Arch (AUR):**
```bash
yay -S monicon
```

**Fedora:**
```bash
sudo dnf install monicon
```

## Usage

### Command-Line Interface

Switch input:
```bash
monicon input dp        # Switch to DisplayPort
monicon input hdmi1     # Switch to HDMI 1
```

Cycle profile:
```bash
monicon profile next    # Cycle to next picture profile
```

Query status:
```bash
monicon status          # Get current input/profile
```

### System Tray (GUI Mode)

Start as system tray application:
```bash
monicon gui
```

Or add to your autostart:
```bash
mkdir -p ~/.config/autostart
cp monicon.desktop ~/.config/autostart/
```

**Keyboard Shortcuts (default):**
- `Ctrl+Super+1` → Switch to DisplayPort
- `Ctrl+Super+2` → Switch to HDMI 1
- `Ctrl+Super+P` → Cycle to next profile

**Customize shortcuts:**
Edit `~/.config/monicon/config.json`:
```json
{
  "shortcuts": {
    "switch_dp": {
      "action": "switch_input_dp",
      "modifiers": ["ctrl", "shift"],
      "key": "d"
    }
  }
}
```

**Rename inputs/profiles:**
```json
{
  "input_names": {
    "dp": "Main DP",
    "hdmi1": "Console"
  },
  "profile_names": {
    "racing": "Competitive",
    "srgb": "Creative"
  }
}
```

## Configuration

Configuration is stored in: `~/.config/monicon/config.json`

**Available options:**
- `monitor_model`: Selected monitor (auto-detected, can override)
- `selected_input_id` / `selected_input_name`: Currently selected input
- `selected_profile_id` / `selected_profile_name`: Currently selected profile
- `autostart`: Start on login
- `minimize_to_tray`: Minimize instead of close
- `confirm_on_quit`: Ask before quitting
- `theme`: `auto`, `light`, or `dark`
- `shortcuts`: Keyboard shortcut definitions
- `input_names`: Custom display names for inputs
- `profile_names`: Custom display names for profiles

## Architecture

Monicon follows **SOLID principles** for clean, maintainable code:

### Project Structure
```
msi_monitor/
├── core/              # Hardware abstraction (HID, monitor interfaces)
├── monitors/          # Monitor-specific implementations
├── config/            # Configuration and settings
├── shortcuts/         # Keyboard shortcut management
├── gui/               # System tray and GUI components
├── utils/             # Helper utilities
├── app.py             # Main application controller
└── cli.py             # Command-line interface
```

### Key Design Principles

**S - Single Responsibility**
- Each module has one reason to change
- `ConfigManager` handles config I/O
- `ShortcutManager` handles keyboard events
- `MonitorController` orchestrates interactions

**O - Open/Closed**
- Monitor implementations can be added without modifying core
- `IMonitor` interface allows swapping implementations
- New monitors: inherit and implement protocol

**L - Liskov Substitution**
- All `IMonitor` implementations are interchangeable
- Controller doesn't care about specific monitor type

**I - Interface Segregation**
- `IHIDDevice` only has HID methods
- `IMonitor` only has monitor control methods
- Clients depend on specific interfaces, not implementation

**D - Dependency Inversion**
- `MonitorController` depends on `IMonitor`, not concrete types
- Dependencies injected at construction
- Easy to test with mock implementations

### Adding Monitor Support

1. Create monitor definition in `msi_monitor/monitors/`
2. Implement `IMonitor` interface
3. Define `MonitorInfo` with inputs/profiles
4. Implement protocol methods: `set_input()`, `next_profile()`, etc.
5. Submit PR!

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Follow code style: `black` + `ruff`
4. Test your changes
5. Submit a PR with description

### For New Monitor Support

If you have a different MSI monitor:

1. **Capture the protocol:**
   ```bash
   sudo modprobe usbmon
   wireshark  # Filter: usb.idVendor == 0x1462
   # Use MSI Gaming Intelligence on Windows VM to trigger commands
   # Export .pcapng file
   ```

2. **Document findings:**
   - Create `msi_monitor/monitors/your_model.py`
   - Add `MonitorInfo` with your inputs/profiles
   - Implement command encoding

3. **Submit PR** with your capture file and implementation

## Protocol Notes

MSI monitors use a **text-based ASCII HID protocol** over USB:

```
Report Format: [ReportID=0x01][ASCII_CMD][0x0D terminator][0x00 padding to 64 bytes]
```

**Example (MPG 341CQR):**
```
Command: 5800130       = Set input to DisplayPort
Response: 5b00130...   = Echo with '8'→'b'
```

See `msi_capture*.pcapng` files for protocol analysis.

## License

GPL-3.0-or-later — See [LICENSE](LICENSE)

Free and open-source software. No proprietary or paid dependencies.

## Support

- 🐛 **Issues:** https://github.com/your-username/monicon/issues
- 💬 **Discussions:** https://github.com/your-username/monicon/discussions
- 📖 **Wiki:** https://github.com/your-username/monicon/wiki

## Acknowledgments

- Protocol reverse-engineered via Wireshark and Windows capture
- Inspired by hardware control tools on macOS/Windows
- Community feedback and monitor contributions
