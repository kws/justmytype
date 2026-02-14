"""Tests for font file discovery and parsing."""

from pathlib import Path

import pytest

from justmytype.parser import find_font_files, parse_font_file


def test_find_font_files_empty_directory(temp_dir: Path) -> None:
    """Test finding fonts in empty directory."""
    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == 0


def test_find_font_files_nonexistent_directory() -> None:
    """Test finding fonts in non-existent directory."""
    fonts = list(find_font_files(Path("/nonexistent/directory")))
    assert len(fonts) == 0


def test_find_font_files_with_ttf(temp_dir: Path) -> None:
    """Test finding .ttf font files."""
    font_file = temp_dir / "test.ttf"
    font_file.touch()

    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == 1
    assert fonts[0] == font_file


def test_find_font_files_with_multiple_extensions(temp_dir: Path) -> None:
    """Test finding fonts with different extensions."""
    extensions = [".ttf", ".otf", ".ttc", ".woff", ".woff2"]
    for ext in extensions:
        (temp_dir / f"test{ext}").touch()

    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == len(extensions)


def test_find_font_files_case_insensitive(temp_dir: Path) -> None:
    """Test finding fonts with uppercase extensions."""
    (temp_dir / "test.TTF").touch()
    (temp_dir / "test.OTF").touch()

    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == 2


def test_find_font_files_recursive(temp_dir: Path) -> None:
    """Test finding fonts recursively in subdirectories."""
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "font.ttf").touch()

    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == 1
    assert fonts[0] == subdir / "font.ttf"


def test_find_font_files_ignores_non_fonts(temp_dir: Path) -> None:
    """Test that non-font files are ignored."""
    (temp_dir / "test.txt").touch()
    (temp_dir / "test.pdf").touch()
    (temp_dir / "test.ttf").touch()

    fonts = list(find_font_files(temp_dir))
    assert len(fonts) == 1
    assert fonts[0].suffix == ".ttf"


def test_parse_font_file_nonexistent() -> None:
    """Test parsing non-existent font file."""
    result = parse_font_file(Path("/nonexistent/font.ttf"))
    assert result is None


def test_parse_font_file_invalid_file(temp_dir: Path) -> None:
    """Test parsing invalid font file."""
    invalid_file = temp_dir / "invalid.ttf"
    invalid_file.write_text("not a font file")

    result = parse_font_file(invalid_file)
    # Should return None for invalid fonts
    assert result is None


def test_parse_font_file_empty_file(temp_dir: Path) -> None:
    """Test parsing empty file."""
    empty_file = temp_dir / "empty.ttf"
    empty_file.touch()

    result = parse_font_file(empty_file)
    # Should return None for empty/invalid fonts
    assert result is None

