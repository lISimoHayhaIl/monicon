"""
Command-line interface for Monicon.

Supports both traditional CLI mode and GUI/tray mode.
"""

import argparse
import logging
import sys

from msi_monitor.monitors import MSIMPEG341CQR


def setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="monicon",
        description="Control MSI gaming monitors from Linux with keybindings and system tray",
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
        choices=["hdmi1", "hdmi2", "dp", "usb_c"],
        help="Target input source",
    )

    # --- profile ---
    p_profile = sub.add_parser("profile", help="Profile control")
    p_profile.add_argument(
        "action",
        choices=["next"],
        help="'next' cycles to next profile",
    )

    # --- status ---
    sub.add_parser("status", help="Query monitor status")

    # --- gui/tray ---
    sub.add_parser("gui", help="Run in system tray mode with global keybindings")

    return parser


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Create monitor instance
        monitor = MSIMPEG341CQR()
        controller = MonitorController(monitor)

        if args.command == "input":
            # CLI mode: switch input
            with monitor:
                monitor.set_input(args.source)
                print(f"✓ Input switched to {args.source.upper()}")

        elif args.command == "profile":
            # CLI mode: cycle profile
            with monitor:
                if args.action == "next":
                    monitor.next_profile()
                    print("✓ Profile cycled")

        elif args.command == "status":
            # CLI mode: query status
            with monitor:
                response = monitor.get_current_input()
                if response:
                    print(f"Status: {response}")
                else:
                    print("No response from monitor")

        elif args.command == "gui":
            # GUI mode: run as system tray with keybindings
            return controller.run()

        return 0

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PermissionError:
        print(
            "Error: Permission denied. Check udev rules:\n"
            "  sudo cp 90-msi-monitor.rules /etc/udev/rules.d/\n"
            "  sudo udevadm control --reload && sudo udevadm trigger\n"
            "  sudo usermod -aG plugdev $USER",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
