"""System font pack for Windows."""

from __future__ import annotations

import os
from pathlib import Path

from justmytype.packs.base import SystemFontPack


class WindowsSystemFontPack(SystemFontPack):
    """System font pack for Windows."""

    def get_font_directories(self) -> list[Path]:
        """Return Windows system font directories.

        Returns:
            List of Path objects for Windows font directories:
            - %WINDIR%/Fonts (System fonts)
            - %LOCALAPPDATA%/Microsoft/Windows/Fonts (User fonts)
        """
        windir = os.environ.get("WINDIR", "C:\\Windows")
        localappdata = os.environ.get("LOCALAPPDATA", "")

        directories: list[Path] = [
            Path(windir) / "Fonts",
        ]

        if localappdata:
            directories.append(Path(localappdata) / "Microsoft" / "Windows" / "Fonts")

        return directories
