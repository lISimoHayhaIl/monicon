# Installation Guide for Monicon

This guide covers installation on all major Linux distributions.

## Prerequisites

All distributions require:
1. **Python 3.9+** — for the application runtime
2. **USB HID library** — for hardware communication
3. **udev rules** — for non-root access to monitor

## System Dependencies

### Arch Linux / CachyOS / Manjaro

```bash
# Install package manager prerequisites
sudo pacman -S base-devel git

# Install runtime dependencies
sudo pacman -S hidapi python-pyqt6 python-pynput
```

### Fedora / RHEL / CentOS

```bash
# Install package manager prerequisites
sudo dnf groupinstall "Development Tools"

# Install runtime dependencies
sudo dnf install hidapi python3-pyqt6 python3-pynput
```

### openSUSE (Leap / Tumbleweed)

```bash
# Install package manager prerequisites
sudo zypper install -t pattern devel_basis

# Install runtime dependencies
sudo zypper install hidapi python3-PyQt6 python3-pynput
```

### Debian / Ubuntu / Linux Mint

```bash
# Install package manager prerequisites
sudo apt-get install build-essential python3-dev

# Install runtime dependencies
sudo apt-get install libhidapi-hidraw0 python3-pyqt6 python3-pynput
```

## Installation Methods

### 1. From AUR (Arch Linux)

```bash
yay -S monicon
# or
paru -S monicon
```

### 2. From Fedora Copr

```bash
sudo dnf copr enable username/monicon
sudo dnf install monicon
```

### 3. From openSUSE Build Service

```bash
# Add repository (Tumbleweed)
sudo zypper addrepo https://build.opensuse.org/repositories/home:username:monicon/openSUSE_Tumbleweed/ monicon
sudo zypper refresh

# Install
sudo zypper install monicon
```

### 4. From Debian/Ubuntu (PPA or manually)

```bash
# Via PPA (if available)
sudo add-apt-repository ppa:username/monicon
sudo apt update
sudo apt install monicon

# Or manual installation
sudo dpkg -i monicon_0.2.0-1_all.deb
sudo apt-get install -f  # Install dependencies
```

### 5. From Source (Development)

```bash
git clone https://github.com/monicon-dev/monicon.git
cd monicon

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Post-Installation Setup

### 1. udev Rules (Required for non-root access)

The installer should automatically install udev rules, but if not:

```bash
# Install rules if not already done
sudo cp 90-msi-monitor.rules /etc/udev/rules.d/

# Reload udev
sudo udevadm control --reload
sudo udevadm trigger

# Add user to plugdev group
sudo usermod -aG plugdev $USER

# Log out and back in for group membership to take effect
```

Verify installation:
```bash
# You should see your monitor
lsusb | grep -i msi

# Check udev rules
ls -la /etc/udev/rules.d/90-msi-monitor.rules
```

### 2. Auto-start (Optional)

To start Monicon automatically on login:

**GNOME / XFCE / Cinnamon:**
```bash
mkdir -p ~/.config/autostart
cp /usr/share/applications/monicon.desktop ~/.config/autostart/
```

**KDE Plasma:**
- System Settings → Startup and Shutdown → Autostart
- Add custom application: `/usr/bin/monicon gui`

**i3 / Openbox / Manual:**
Add to your startup configuration (~/.xinitrc, ~/.config/i3/config, etc.):
```bash
monicon gui &
```

### 3. Verify Installation

```bash
# Check if monicon command works
monicon --help

# Try a simple command
monicon status

# Test GUI mode (should show tray icon)
monicon gui
```

## Building Packages Locally

### Arch (makepkg)

```bash
cd packaging/arch
makepkg -si
```

### Fedora (rpmbuild)

```bash
cd packaging/fedora
rpmbuild -ba monicon.spec
```

### openSUSE (osc)

```bash
cd packaging/opensuse
osc build
```

### Debian (debuild)

```bash
cd packaging/debian
debuild -us -uc
```

## Troubleshooting

### "Device not found" error

```bash
# Check if monitor is connected
lsusb | grep -i msi

# Check if udev rules are working
ls -l /dev/hidraw*

# Try with sudo (if udev rules not working)
sudo monicon status
```

### "Permission denied" when accessing device

```bash
# Check if user is in plugdev group
groups $USER

# If not, add and log out/in
sudo usermod -aG plugdev $USER

# Or reload udev rules
sudo udevadm control --reload
sudo udevadm trigger
```

### GUI doesn't start / tray icon not visible

```bash
# Run with verbose output
monicon -v gui

# Check if PyQt6 is properly installed
python3 -c "from PyQt6 import QtWidgets; print('PyQt6 OK')"

# Check if pynput is installed
python3 -c "from pynput import keyboard; print('pynput OK')"
```

### Shortcuts not working

```bash
# Try with verbose output
monicon -v gui

# Check if pynput keyboard listener is working
python3 -c "from pynput.keyboard import Listener; print('pynput listener OK')"

# Check XDG config
cat ~/.config/monicon/config.json
```

## Updating

### From package manager

```bash
# Arch
sudo pacman -Syu monicon

# Fedora
sudo dnf update monicon

# openSUSE
sudo zypper update monicon

# Debian/Ubuntu
sudo apt update && sudo apt upgrade monicon
```

### From source

```bash
cd ~/monicon
git pull origin main
pip install -e .
```

## Uninstallation

### From package manager

```bash
# Arch
sudo pacman -R monicon

# Fedora
sudo dnf remove monicon

# openSUSE
sudo zypper remove monicon

# Debian/Ubuntu
sudo apt remove monicon
```

### From source

```bash
# If installed in venv, just delete the venv
rm -rf ~/monicon/venv

# If system-wide, uninstall the package
pip uninstall monicon
```

## Getting Help

- **Issues**: https://github.com/monicon-dev/monicon/issues
- **Discussions**: https://github.com/monicon-dev/monicon/discussions
- **Wiki**: https://github.com/monicon-dev/monicon/wiki
