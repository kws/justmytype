"""Font file discovery and metadata parsing."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

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
    try:
        font = TTFont(str(path))

        # Extract family name from name table (name ID 1 = Family name)
        name_table = font.get("name")
        if name_table is None:
            return None

        # Check if this is a variable font (has 'fvar' table)
        is_variable_font = font.get("fvar") is not None

        # For variable fonts, prefer nameID 16 (Typographic Family Name)
        # which contains the base family name without optical size suffixes
        if is_variable_font:
            # Try nameID 16 first (Typographic Family Name)
            family = name_table.getDebugName(16)
            if not family:
                # Fallback to nameID 1 and strip optical size patterns
                family = name_table.getDebugName(1)
                if family:
                    # Strip optical size patterns (e.g., " 9pt", " 10pt", " 12.5pt")
                    # Pattern matches: optional whitespace, digits, optional decimal, "pt", optional trailing whitespace
                    family = re.sub(r"\s+\d+(\.\d+)?pt\s*$", "", family).strip()
        else:
            # For non-variable fonts, use nameID 1 as before
            family = name_table.getDebugName(1)

        if not family:
            return None

        # Extract PostScript name (name ID 6)
        postscript_name = name_table.getDebugName(6)

        # Extract weight from OS/2 table
        os2 = font.get("OS/2")
        weight: int | None = None
        style = "normal"
        width: str | None = None

        if os2 is not None:
            # Extract weight (usWeightClass: 100-900)
            weight = os2.usWeightClass if hasattr(os2, "usWeightClass") else None

            # Extract style from fsSelection (bit 0 = italic)
            if hasattr(os2, "fsSelection") and os2.fsSelection & 0x01:
                style = "italic"

            # Extract width/stretch from usWidthClass
            if hasattr(os2, "usWidthClass"):
                width = WIDTH_MAP.get(os2.usWidthClass, "normal")

        # Extract variant from name table (name ID 2 = Subfamily)
        variant = name_table.getDebugName(2)  # Subfamily name

        return FontInfo(
            path=path,
            family=family,
            weight=weight,
            style=style,
            width=width,
            postscript_name=postscript_name,
            variant=variant,
        )
    except Exception:
        # Return None for any parsing errors (invalid font, corrupted file, etc.)
        return None
