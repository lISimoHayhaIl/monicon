"""
Monicon — Cross-platform MSI Monitor Control Application

A modern, SOLID-principle-based system tray application for controlling MSI gaming monitors
on Linux with support for input switching, profile management, and global keybindings.
"""

# Version scheme: MAJOR.MINOR.PATCH.BUILD
# BUILD increments on every change made to the codebase (however small), so a
# running process's exact code state is always visually distinguishable — this
# lets the user tell at a glance (in the tray tooltip / About dialog / window
# title) whether they are looking at a freshly-restarted process or a stale
# one left running from before a fix, which was a real source of confusion
# during development (identical-looking "0.1.0" across multiple bugfix
# sessions gave no way to tell whether a fix was actually loaded).
__version__ = "0.1.0.101"
__author__ = "Monicon Contributors"
__license__ = "GPL-3.0-or-later"
