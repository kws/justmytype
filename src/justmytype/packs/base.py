"""Base class for system font packs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class SystemFontPack(ABC):
    """Abstract base class for platform-specific system font packs.

    This implements the standard FontPack protocol. Each platform
    (Darwin, Windows, Linux) has its own subclass that returns
    platform-specific font directories.
    """

    @abstractmethod
    def get_font_directories(self) -> list[Path]:
        """Return platform-specific system font directories.

        Returns:
            List of Path objects pointing to system font directories.
        """
        ...

    def get_priority(self) -> int:
        """Return the priority of this pack (0 = lowest).

        System fonts have the lowest priority to ensure that bundled
        fonts (priority 100) always take precedence.

        Returns:
            Priority value (0 for system fonts).
        """
        return 0

    def get_name(self) -> str:
        """Return the canonical name for this pack (used in blocklist).

        Returns:
            String identifier "system-fonts".
        """
        return "system-fonts"
