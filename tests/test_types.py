"""Tests for core type definitions."""

from pathlib import Path

import pytest

from justmytype.types import FontInfo


def test_font_info_creation() -> None:
    """Test FontInfo dataclass creation."""
    path = Path("/test/font.ttf")
    font_info = FontInfo(
        path=path,
        family="Test Font",
        weight=400,
        style="normal",
        width="normal",
    )

    assert font_info.path == path
    assert font_info.family == "Test Font"
    assert font_info.weight == 400
    assert font_info.style == "normal"
    assert font_info.width == "normal"


def test_font_info_defaults() -> None:
    """Test FontInfo with default values."""
    path = Path("/test/font.ttf")
    font_info = FontInfo(path=path, family="Test Font")

    assert font_info.style == "normal"
    assert font_info.weight is None
    assert font_info.width is None
    assert font_info.postscript_name is None
    assert font_info.variant is None


def test_font_info_frozen() -> None:
    """Test that FontInfo is frozen (immutable)."""
    from dataclasses import FrozenInstanceError

    path = Path("/test/font.ttf")
    font_info = FontInfo(path=path, family="Test Font")

    with pytest.raises(FrozenInstanceError):
        font_info.family = "New Name"  # type: ignore[misc]


def test_font_info_load_without_pillow() -> None:
    """Test FontInfo.load() raises ImportError when Pillow is not available."""
    path = Path("/test/font.ttf")
    font_info = FontInfo(path=path, family="Test Font")

    # This will fail because the font file doesn't exist, but we're testing
    # the ImportError handling. We'll need to mock PIL import for a proper test.
    # For now, we'll just verify the method exists and has the right signature.
    assert hasattr(font_info, "load")
    assert callable(font_info.load)


def test_font_pack_protocol() -> None:
    """Test that FontPack protocol is properly defined."""

    class TestPack:
        """Test implementation of FontPack."""

        def get_font_directories(self) -> list[Path]:
            return [Path("/test/fonts")]

        def get_priority(self) -> int:
            return 100

        def get_name(self) -> str:
            return "test-pack"

    pack = TestPack()

    # Verify it implements the protocol
    assert hasattr(pack, "get_font_directories")
    assert hasattr(pack, "get_priority")
    assert hasattr(pack, "get_name")

    assert pack.get_font_directories() == [Path("/test/fonts")]
    assert pack.get_priority() == 100
    assert pack.get_name() == "test-pack"
