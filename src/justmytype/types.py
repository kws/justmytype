"""Core type definitions for JustMyType."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PIL import ImageFont


class FontPack(Protocol):
    """Protocol that all font sources must implement."""

    def get_font_directories(self) -> list[Path]:
        """Return list of directories containing font files.

        Returns:
            List of Path objects pointing to directories with font files.
        """
        ...

    def get_priority(self) -> int:
        """Return priority for this pack (higher = processed first, overrides lower priority).

        Standard priorities:
        - User Font Packs: 100
        - System Font Pack: 0

        Returns:
            Integer priority value (higher = higher priority).
        """
        ...

    def get_name(self) -> str:
        """Return canonical name for this pack (used in blocklist).

        Must be unique and stable. System pack uses "system-fonts".

        Returns:
            String identifier for this font pack.
        """
        ...


@dataclass(frozen=True, slots=True)
class FontInfo:
    """Information about a discovered font."""

    path: Path
    """Path to the font file."""

    family: str
    """Font family name."""

    weight: int | None = None
    """Font weight (100-900, None if unknown)."""

    style: str = "normal"
    """Font style: 'normal' or 'italic'."""

    width: str | None = None
    """Font width/stretch (e.g., 'normal', 'condensed', 'expanded', None if unknown)."""

    postscript_name: str | None = None
    """PostScript name (e.g., 'Roboto-BoldItalic') for native OS APIs."""

    variant: str | None = None
    """Font variant (e.g., 'Regular', 'Bold', 'Italic', 'Bold Italic')."""

    def load(self, size: int) -> ImageFont.FreeTypeFont | None:
        """Load this font as a PIL ImageFont.

        This method imports PIL only when called, keeping JustMyType
        decoupled from Pillow for users who don't need it.

        Args:
            size: Font size in points.

        Returns:
            PIL ImageFont object, or None if loading fails.

        Raises:
            ImportError: If Pillow is not installed.
        """
        try:
            from PIL import ImageFont

            return ImageFont.truetype(str(self.path), size=size)
        except ImportError as e:
            raise ImportError(
                "Pillow (PIL) is required to load fonts. Install with: pip install Pillow"
            ) from e
        except Exception:
            return None

