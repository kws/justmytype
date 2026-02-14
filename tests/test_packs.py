"""Tests for system font packs."""

import platform
from pathlib import Path

import pytest

from justmytype.packs.base import SystemFontPack
from justmytype.packs.darwin import DarwinSystemFontPack
from justmytype.packs.factory import create_system_font_pack
from justmytype.packs.linux import LinuxSystemFontPack
from justmytype.packs.windows import WindowsSystemFontPack


def test_system_font_pack_base() -> None:
    """Test SystemFontPack base class."""
    # Can't instantiate abstract class directly
    with pytest.raises(TypeError):
        SystemFontPack()  # type: ignore[abstract]


def test_darwin_system_font_pack() -> None:
    """Test DarwinSystemFontPack."""
    pack = DarwinSystemFontPack()

    assert pack.get_priority() == 0
    assert pack.get_name() == "system-fonts"

    directories = pack.get_font_directories()
    assert len(directories) == 3
    assert Path("/System/Library/Fonts") in directories
    assert Path("/Library/Fonts") in directories
    assert (Path.home() / "Library" / "Fonts") in directories


def test_windows_system_font_pack() -> None:
    """Test WindowsSystemFontPack."""
    pack = WindowsSystemFontPack()

    assert pack.get_priority() == 0
    assert pack.get_name() == "system-fonts"

    directories = pack.get_font_directories()
    assert len(directories) >= 1
    # Should include Windows Fonts directory
    assert any("Fonts" in str(d) for d in directories)


def test_linux_system_font_pack() -> None:
    """Test LinuxSystemFontPack."""
    pack = LinuxSystemFontPack()

    assert pack.get_priority() == 0
    assert pack.get_name() == "system-fonts"

    directories = pack.get_font_directories()
    assert len(directories) >= 4
    assert (Path.home() / ".fonts") in directories
    assert Path("/usr/share/fonts") in directories
    assert Path("/usr/local/share/fonts") in directories


def test_create_system_font_pack() -> None:
    """Test create_system_font_pack factory function."""
    pack = create_system_font_pack()

    assert isinstance(pack, SystemFontPack)
    assert pack.get_priority() == 0
    assert pack.get_name() == "system-fonts"

    # Should return appropriate pack for current platform
    system = platform.system()
    if system == "Darwin":
        assert isinstance(pack, DarwinSystemFontPack)
    elif system == "Windows":
        assert isinstance(pack, WindowsSystemFontPack)
    elif system == "Linux":
        assert isinstance(pack, LinuxSystemFontPack)


def test_system_font_pack_implements_protocol() -> None:
    """Test that system font packs implement FontPack protocol."""
    pack = create_system_font_pack()

    # Verify protocol methods exist
    assert hasattr(pack, "get_font_directories")
    assert hasattr(pack, "get_priority")
    assert hasattr(pack, "get_name")

    # Verify methods return correct types
    directories = pack.get_font_directories()
    assert isinstance(directories, list)
    assert all(isinstance(d, Path) for d in directories)

    priority = pack.get_priority()
    assert isinstance(priority, int)

    name = pack.get_name()
    assert isinstance(name, str)
    assert name == "system-fonts"
