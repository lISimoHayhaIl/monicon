# msi-monitor-ctl

A Linux command-line tool to control MSI MPG monitors over USB HID —
no Windows software, no VM required.

Currently tested on: **MSI MPG 341CQR QD-OLED X36**

## Features

- Switch input source (DP ↔ HDMI) from the terminal or a keyboard shortcut
- Cycle picture profiles (Eco, FPS, Racing, RPG, sRGB, Movie, …)
- No background daemon required — runs on demand

## Installation

### 1. System dependency

```bash
# Arch / CachyOS
sudo pacman -S hidapi

# Debian / Ubuntu
sudo apt install libhidapi-hidraw0
```

### 2. udev rule (required for access without sudo)

```bash
sudo cp 90-msi-monitor.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger
sudo usermod -aG plugdev $USER
# Log out and back in for the group change to take effect
```

### 3. Install the tool

```bash
pip install --user hid
pip install --user .
```

Or for development (editable install):

```bash
pip install --user -e .
```

## Usage

```bash
# Switch to DisplayPort
msi-monitor-ctl input dp

# Switch to HDMI 1
msi-monitor-ctl input hdmi1

# Cycle to next picture profile
msi-monitor-ctl profile next

# Query monitor status
msi-monitor-ctl status

# Verbose / debug output
msi-monitor-ctl -v input dp
```

## Keyboard shortcuts

You can bind `msi-monitor-ctl input dp` to any hotkey using your desktop
environment's shortcut manager, or tools like `sxhkd`, `xbindkeys`, or
a custom `systemd --user` service with `evdev`.

Example with `sxhkd` (`~/.config/sxhkd/sxhkdrc`):

```
super + F1
    msi-monitor-ctl input dp

super + F2
    msi-monitor-ctl input hdmi1
```

## Protocol notes

The monitor uses a **text-based ASCII HID protocol** over USB (Interface 0,
VID=0x1462, PID=0x3fa4). Commands are 64-byte HID reports:

```
[ReportID=0x01][ASCII_CMD][0x0D][0x00 padding…]
```

Known commands (reverse-engineered via usbmon/Wireshark capture):

| Command bytes | Meaning                        |
|---------------|--------------------------------|
| `5800110`     | Set input → HDMI 1             |
| `5800120`     | Set input → HDMI 2 (unverified)|
| `5800130`     | Set input → DisplayPort        |
| `5800140`     | Query current input            |
| `5800150`     | Query status                   |
| `5800190`     | Cycle to next picture profile  |
| `6800;30`     | Heartbeat / keepalive (A)      |

Responses echo the command with `'8'` replaced by `'b'`:
`5800130` → `5b00130DE2A015C00725`

## Contributing

Protocol capture procedure (for adding new features):

1. `sudo modprobe usbmon`
2. Start Wireshark on `usbmon1`, filter `usb.idVendor == 0x1462`
3. Pass USB device to Windows VM, use MSI Gaming Intelligence software
4. Change the setting you want to reverse-engineer
5. Save `.pcapng`, analyse with the scripts in `tools/`

## Supported monitors

- MSI MPG 341CQR QD-OLED X36 (VID=0x1462, PID=0x3fa4) ✓

Other MSI monitors using the same USB HID interface may work — open an
issue with your `lsusb -v` output to add support.

## License

GPL-3.0-or-later
