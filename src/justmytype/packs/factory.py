"""Factory function for creating platform-specific system font packs."""

from __future__ import annotations

import platform

from justmytype.packs.base import SystemFontPack
from justmytype.packs.darwin import DarwinSystemFontPack
from justmytype.packs.linux import LinuxSystemFontPack
from justmytype.packs.windows import WindowsSystemFontPack


def create_system_font_pack() -> SystemFontPack:
    """Create the appropriate system font pack for the current platform.

    Returns:
        SystemFontPack instance for the current platform.

    Raises:
        NotImplementedError: If the platform is not supported.
    """
    system = platform.system()

    if system == "Darwin":
        return DarwinSystemFontPack()
    elif system == "Windows":
        return WindowsSystemFontPack()
    elif system == "Linux":
        return LinuxSystemFontPack()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

