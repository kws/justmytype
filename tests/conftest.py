"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from justmytype.core import FontRegistry
from justmytype.types import FontInfo


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def font_registry() -> FontRegistry:
    """Create a FontRegistry instance for testing."""
    return FontRegistry()


@pytest.fixture
def empty_font_registry() -> FontRegistry:
    """Create a FontRegistry instance with system fonts blocked."""
    return FontRegistry(blocklist={"system-fonts"})


class MockFontPack:
    """Mock FontPack for testing."""

    def __init__(
        self,
        directories: list[Path],
        priority: int = 100,
        name: str = "test-pack",
    ) -> None:
        """Initialize mock font pack.

        Args:
            directories: List of font directories.
            priority: Priority of this pack.
            name: Name of this pack.
        """
        self.directories = directories
        self._priority = priority
        self._name = name

    def get_font_directories(self) -> list[Path]:
        """Return font directories."""
        return self.directories

    def get_priority(self) -> int:
        """Return priority."""
        return self._priority

    def get_name(self) -> str:
        """Return pack name."""
        return self._name


def create_test_font_info(
    path: Path,
    family: str = "Test Font",
    weight: int | None = 400,
    style: str = "normal",
    width: str | None = "normal",
) -> FontInfo:
    """Create a test FontInfo object.

    Args:
        path: Path to font file.
        family: Font family name.
        weight: Font weight.
        style: Font style.
        width: Font width.

    Returns:
        FontInfo object.
    """
    return FontInfo(
        path=path,
        family=family,
        weight=weight,
        style=style,
        width=width,
        postscript_name=f"{family.replace(' ', '')}-{style.title()}",
        variant="Regular",
    )
