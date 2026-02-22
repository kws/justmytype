"""Font file discovery and metadata parsing."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from justmytype.types import FontInfo

# Font file extensions to scan for
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}

# Weight mapping for string-to-integer conversion
WEIGHT_MAP = {
    "thin": 100,
    "hairline": 100,
    "extralight": 200,
    "ultralight": 200,
    "light": 300,
    "book": 350,
    "regular": 400,
    "normal": 400,
    "medium": 500,
    "demibold": 600,
    "semibold": 600,
    "demi": 600,
    "bold": 700,
    "extrabold": 800,
    "ultrabold": 800,
    "black": 900,
    "heavy": 900,
    "extrablack": 950,
    "ultrablack": 950,
}

# OS/2 usWidthClass to CSS width mapping
WIDTH_MAP = {
    1: "ultra-condensed",
    2: "extra-condensed",
    3: "condensed",
    4: "semi-condensed",
    5: "normal",
    6: "semi-expanded",
    7: "expanded",
    8: "extra-expanded",
    9: "ultra-expanded",
}


def find_font_files(directory: Path) -> Iterator[Path]:
    """Recursively find all font files in a directory.

    Scans for common font file extensions (.ttf, .otf, .ttc, .woff, .woff2)
    and follows symlinks. Gracefully handles permission errors and missing
    directories.

    Args:
        directory: Directory to scan for font files.

    Yields:
        Path objects to font files found in the directory tree.
    """
    if not directory.exists():
        return

    try:
        for item in directory.iterdir():
            try:
                if item.is_symlink():
                    # Resolve symlink and check if it's a directory
                    target = item.resolve()
                    if target.is_dir():
                        yield from find_font_files(target)
                    elif target.suffix.lower() in FONT_EXTENSIONS:
                        yield target
                elif item.is_dir():
                    yield from find_font_files(item)
                elif item.suffix.lower() in FONT_EXTENSIONS:
                    yield item
            except (OSError, PermissionError):
                # Skip files/directories we can't access
                continue
    except (OSError, PermissionError):
        # Skip directories we can't read
        return


def parse_font_metadata(path: Path) -> dict[str, Any] | None:
    """Extract metadata from a font file using fonttools.

    Single source of truth for reading name table and OS/2. Used by
    parse_font_file (registry path) and by pack-tools manifest generation.

    Args:
        path: Path to the font file.

    Returns:
        Dict with keys family, style, weight, width, postscript_name, variant;
        or None if parsing fails.
    """
    try:
        font = TTFont(str(path))
        name_table = font.get("name")
        if name_table is None:
            return None

        is_variable_font = font.get("fvar") is not None
        if is_variable_font:
            family = name_table.getDebugName(16)
            if not family:
                family = name_table.getDebugName(1)
                if family:
                    family = re.sub(r"\s+\d+(\.\d+)?pt\s*$", "", family).strip()
        else:
            family = name_table.getDebugName(1)

        if not family:
            return None

        postscript_name = name_table.getDebugName(6)
        variant = name_table.getDebugName(2)  # Subfamily (name ID 2)

        os2 = font.get("OS/2")
        weight: int | None = None
        style = "normal"
        width: str | None = None
        if os2 is not None:
            weight = os2.usWeightClass if hasattr(os2, "usWeightClass") else None
            if hasattr(os2, "fsSelection") and os2.fsSelection & 0x01:
                style = "italic"
            if hasattr(os2, "usWidthClass"):
                width = WIDTH_MAP.get(os2.usWidthClass, "normal")

        return {
            "family": family,
            "style": style,
            "weight": weight,
            "width": width,
            "postscript_name": postscript_name,
            "variant": variant,
        }
    except Exception:
        return None


def parse_font_file(path: Path) -> FontInfo | None:
    """Parse font file and extract metadata using fonttools.

    Uses fonttools to parse binary OpenType tables (name, OS/2) to extract
    the true family name, weight, style, and width. This is the only reliable
    way to get font metadata—filename parsing fails ~30% of the time.

    Args:
        path: Path to the font file to parse.

    Returns:
        FontInfo object with parsed metadata, or None if parsing fails.
    """
    meta = parse_font_metadata(path)
    if meta is None:
        return None
    return FontInfo(path=path, **meta)
