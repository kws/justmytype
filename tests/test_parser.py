"""Tests for font file discovery and parsing."""

from pathlib import Path

import pytest

from justmytype.parser import find_font_files, parse_font_file, parse_font_metadata


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


def test_parse_font_metadata_returns_dict_with_variant() -> None:
    """parse_font_metadata returns a dict including variant for a real font."""
    fixture_path = Path(__file__).parent / "pack_fixture" / "fonts" / "fixture.ttf"
    if not fixture_path.exists():
        pytest.skip("pack_fixture/fonts/fixture.ttf not found")
    meta = parse_font_metadata(fixture_path)
    if meta is None:
        pytest.skip("fixture is not a parseable font (e.g. placeholder)")
    assert "family" in meta
    assert "style" in meta
    assert "weight" in meta
    assert "width" in meta
    assert "postscript_name" in meta
    assert "variant" in meta
    assert meta.get("variant") is not None  # e.g. "Regular"


def test_parse_font_file_and_parse_font_metadata_agree_on_variant() -> None:
    """parse_font_file and parse_font_metadata return the same variant for the same path."""
    fixture_path = Path(__file__).parent / "pack_fixture" / "fonts" / "fixture.ttf"
    if not fixture_path.exists():
        pytest.skip("pack_fixture/fonts/fixture.ttf not found")
    meta = parse_font_metadata(fixture_path)
    font_info = parse_font_file(fixture_path)
    if meta is None or font_info is None:
        pytest.skip("fixture is not a parseable font (e.g. placeholder)")
    assert font_info.variant == meta.get("variant")
