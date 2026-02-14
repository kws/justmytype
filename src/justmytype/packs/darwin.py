"""System font pack for macOS (Darwin)."""

from __future__ import annotations

from pathlib import Path

from justmytype.packs.base import SystemFontPack


class DarwinSystemFontPack(SystemFontPack):
    """System font pack for macOS."""

    def get_font_directories(self) -> list[Path]:
        """Return macOS system font directories.

        Returns:
            List of Path objects for macOS font directories:
            - /System/Library/Fonts (System fonts)
            - /Library/Fonts (System-wide fonts)
            - ~/Library/Fonts (User fonts)
        """
        return [
            Path("/System/Library/Fonts"),  # System fonts
            Path("/Library/Fonts"),  # System-wide fonts
            Path.home() / "Library" / "Fonts",  # User fonts
        ]

