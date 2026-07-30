Name:           monicon
Version:        0.2.0
Release:        1
Summary:        Modern system tray application for MSI monitor control on Linux
License:        GPL-3.0-or-later
URL:            https://github.com/monicon-dev/monicon
Source:         %{url}/archive/feat/refactor-solid-tray-gui.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.9
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel

Requires:       python3 >= 3.9
Requires:       python3-pynput >= 1.7
Requires:       python3-PyQt6 >= 6.0
Requires:       libhidapi0

%description
Monicon is a modern system tray application for controlling MSI gaming monitors
on Linux. Supports input switching, profile management, global keyboard shortcuts,
and works on any Linux desktop environment.

Features:
- System tray icon with context menu
- Input source switching (HDMI, DisplayPort, USB-C)
- Profile cycling and management
- Global keyboard shortcuts (customizable)
- Custom names for inputs and profiles
- XDG configuration directories
- Cross-desktop compatible (GNOME, KDE, XFCE, i3, etc.)

%prep
%setup -q -n monicon-feat/refactor-solid-tray-gui

%build
python3 -m build --wheel --no-isolation

%install
python3 -m pip install --root=%{buildroot} --no-deps --no-index --find-links dist/ monicon

# Install udev rules
install -D -m 0644 90-msi-monitor.rules %{buildroot}%{_udevrulesdir}/90-msi-monitor.rules

# Install desktop entry
mkdir -p %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/monicon.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Monicon
Comment=Control MSI gaming monitors
Exec=monicon gui
Icon=monicon
Categories=Utility;Hardware;
Terminal=false
StartupNotify=false
EOF

%post
# Reload udev rules
udevadm control --reload
udevadm trigger

%files
%license LICENSE
%doc README.md
%{_bindir}/monicon
%{_udevrulesdir}/90-msi-monitor.rules
%{_datadir}/applications/monicon.desktop
%{python3_sitelib}/msi_monitor/
%{python3_sitelib}/monicon-*.dist-info/

%changelog
* Thu Jul 30 2024 Monicon Project <monicon@example.com> - 0.2.0-1
- Initial release with refactored SOLID architecture
- System tray GUI with PyQt6
- Global keyboard shortcut support
- Pluggable monitor definitions
