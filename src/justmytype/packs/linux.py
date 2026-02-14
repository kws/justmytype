"""System font pack for Linux."""

from __future__ import annotations

import os
from pathlib import Path

from justmytype.packs.base import SystemFontPack


class LinuxSystemFontPack(SystemFontPack):
    """System font pack for Linux."""

    def get_font_directories(self) -> list[Path]:
        """Return Linux system font directories.

        Returns:
            List of Path objects for Linux font directories:
            - ~/.fonts (Legacy user fonts)
            - /usr/share/fonts (System fonts)
            - /usr/local/share/fonts (Local system fonts)
            - $XDG_DATA_HOME/fonts (User fonts, XDG Base Directory)
            - /run/host/fonts (Flatpak/Snap sandbox fonts)
        """
        xdg_data_home = os.environ.get(
            "XDG_DATA_HOME", Path.home() / ".local" / "share"
        )

        return [
            Path.home() / ".fonts",  # Legacy user fonts
            Path("/usr/share/fonts"),  # System fonts
            Path("/usr/local/share/fonts"),  # Local system fonts
            Path(xdg_data_home) / "fonts",  # User fonts (XDG Base Directory)
            Path("/run/host/fonts"),  # Flatpak/Snap sandbox fonts
        ]

