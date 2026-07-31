Name:           monicon
Version:        0.2.0
Release:        1%{?dist}
Summary:        Modern system tray application for MSI monitor control on Linux

License:        GPLv3+
URL:            https://github.com/monicon-dev/monicon
Source0:        %{url}/archive/feat/refactor-solid-tray-gui.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-build
BuildRequires:  python3-installer

Requires:       python3 >= 3.9
Requires:       python3-pynput >= 1.7
Requires:       python3-pyqt6 >= 6.0
Requires:       python3-hid
Requires:       hidapi

# Old package name
Obsoletes:      msi-monitor-ctl < 0.2.0
Provides:       msi-monitor-ctl = %{version}-%{release}

%description
Monicon is a modern system tray application for controlling MSI gaming monitors
on Linux. Features include input switching, profile management, global keyboard
shortcuts, and cross-desktop environment compatibility.

%prep
%autosetup -n monicon-feat/refactor-solid-tray-gui

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files msi_monitor

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

# Install the tray/launcher icon into the hicolor theme so desktop
# environments can resolve "Icon=monicon" from the .desktop file above.
for size in 16 22 24 32 48 64 128 256; do
    install -Dm644 "msi_monitor/gui/assets/monicon-${size}.png" \
        "%{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/monicon.png"
done
install -Dm644 msi_monitor/gui/assets/monicon.svg \
    "%{buildroot}%{_datadir}/icons/hicolor/scalable/apps/monicon.svg"

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/monicon
%{_udevrulesdir}/90-msi-monitor.rules
%{_datadir}/applications/monicon.desktop
%{_datadir}/icons/hicolor/*/apps/monicon.png
%{_datadir}/icons/hicolor/scalable/apps/monicon.svg

%post
# Reload udev rules
udevadm control --reload
udevadm trigger

%changelog
* Thu Jul 30 2024 Monicon Project <monicon@example.com> - 0.2.0-1
- Major refactor with SOLID principles
- System tray GUI with PyQt6
- Global keyboard shortcut support
- Pluggable monitor definitions
- Configuration management with XDG directories
