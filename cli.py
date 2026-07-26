"""
msi-monitor-ctl — command-line interface

Usage examples:
    msi-monitor-ctl input dp
    msi-monitor-ctl input hdmi1
    msi-monitor-ctl profile next
    msi-monitor-ctl status
"""

import argparse
import logging
import sys

from .device import MSIMonitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="msi-monitor-ctl",
        description="Control MSI MPG 341CQR monitor settings from Linux",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- input ---
    p_input = sub.add_parser("input", help="Switch input source")
    p_input.add_argument(
        "source",
        choices=["hdmi1", "hdmi2", "dp"],
        help="Target input source",
    )

    # --- profile ---
    p_profile = sub.add_parser("profile", help="Picture profile control")
    p_profile.add_argument(
        "action",
        choices=["next"],
        help="'next' cycles through profiles (Eco→FPS→Racing→RPG→sRGB→Movie→...)",
    )

    # --- status ---
    sub.add_parser("status", help="Query monitor status")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        with MSIMonitor() as mon:
            if args.command == "input":
                mon.set_input(args.source)
                print(f"✓ Input switched to {args.source.upper()}")

            elif args.command == "profile":
                if args.action == "next":
                    response = mon.next_profile()
                    print(f"✓ Profile cycled")
                    if response:
                        print(f"  Response: {response}")

            elif args.command == "status":
                response = mon.query_status()
                if response:
                    print(f"Status: {response}")
                else:
                    print("No response from monitor (timeout)")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(
            "Error: Permission denied. Add udev rule or run with sudo.\n"
            "  sudo cp 90-msi-monitor.rules /etc/udev/rules.d/\n"
            "  sudo udevadm control --reload && sudo udevadm trigger",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
