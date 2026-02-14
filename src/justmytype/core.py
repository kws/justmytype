"""Font registry for discovering and resolving fonts."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from justmytype.matcher import (
    calculate_distance,
    try_family_aliases,
)
from justmytype.packs.factory import create_system_font_pack
from justmytype.parser import find_font_files, parse_font_file
from justmytype.types import FontInfo, FontPack

if TYPE_CHECKING:
    from PIL import ImageFont


class FontRegistry:
    """Registry for discovering and resolving fonts from multiple sources.

    The registry discovers fonts from:
    1. System font packs (platform-specific, priority 0)
    2. Font packs via EntryPoints (priority 100)

    Fonts are discovered lazily on first use and cached in memory.
    Higher priority fonts override lower priority fonts.
    """

    def __init__(self, blocklist: set[str] | None = None) -> None:
        """Initialize font registry.

        Args:
            blocklist: Set of font pack names to exclude from discovery.
                Can also be set via FONT_DISCOVERY_BLOCKLIST environment variable.
        """
        self._fonts: dict[str, list[FontInfo]] = {}  # family -> [FontInfo]
        self._font_pack_priorities: dict[Path, int] = {}  # path -> priority
        self._font_pack_names: dict[Path, str] = {}  # path -> pack name
        self._discovered = False
        self._blocklist = self._parse_blocklist(blocklist)

    def _parse_blocklist(self, blocklist: set[str] | None) -> set[str]:
        """Parse blocklist from constructor and environment variable.

        Args:
            blocklist: Blocklist from constructor.

        Returns:
            Merged set of blocked pack names.
        """
        result = set(blocklist) if blocklist else set()

        # Merge with environment variable
        env_blocklist = os.environ.get("FONT_DISCOVERY_BLOCKLIST", "")
        if env_blocklist:
            result.update(
                name.strip() for name in env_blocklist.split(",") if name.strip()
            )

        return result

    def _get_entry_points(self) -> Iterator[tuple[str, FontPack]]:
        """Get font packs from EntryPoints.

        Yields:
            Tuples of (entry_point_name, FontPack instance).
        """
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group="justmytype.packs")
        except ImportError:
            # Python < 3.10 fallback
            try:
                import importlib_metadata

                eps = importlib_metadata.entry_points(group="justmytype.packs")
            except ImportError:
                return

        for ep in eps:
            try:
                factory = ep.load()
                pack = factory()

                # Verify it implements FontPack protocol
                if not (
                    hasattr(pack, "get_font_directories")
                    and hasattr(pack, "get_priority")
                    and hasattr(pack, "get_name")
                ):
                    continue

                yield (ep.name, pack)
            except Exception:
                # Skip invalid entry points
                continue

    def discover(self) -> None:
        """Discover fonts from all registered packs (high-priority first).

        Fonts are discovered lazily—this method only runs once per registry instance.
        Higher priority fonts override lower priority fonts in the cache.
        """
        if self._discovered:
            return

        # Collect all packs with their priorities
        packs: list[tuple[list[Path], int, str]] = []

        # 1. Load System Font Pack (unless blocked)
        if "system-fonts" not in self._blocklist:
            try:
                system_pack = create_system_font_pack()
                system_dirs = system_pack.get_font_directories()
                packs.append(
                    (
                        system_dirs,
                        system_pack.get_priority(),
                        system_pack.get_name(),
                    )
                )
            except NotImplementedError:
                # Unsupported platform, skip system fonts
                pass

        # 2. Load External Packs via EntryPoints
        for pack_name, pack in self._get_entry_points():
            if pack_name in self._blocklist:
                continue  # Skip blocked packs

            try:
                dirs = pack.get_font_directories()
                priority = pack.get_priority()
                name = pack.get_name()
                packs.append((dirs, priority, name))
            except Exception:
                continue

        # Sort packs by priority (highest first)
        packs.sort(key=lambda x: x[1], reverse=True)

        # Process packs in priority order
        for dirs, priority, pack_name in packs:
            for dir_path in dirs:
                self._scan_directory(dir_path, priority=priority, pack_name=pack_name)

        self._discovered = True

    def _scan_directory(self, dir_path: Path, priority: int, pack_name: str) -> None:
        """Scan directory and add fonts, respecting priority.

        Args:
            dir_path: Directory to scan for fonts.
            priority: Priority of the font pack this directory belongs to.
            pack_name: Name of the font pack.
        """
        for font_file in find_font_files(dir_path):
            font_info = parse_font_file(font_file)
            if font_info is None:
                continue

            family_lower = font_info.family.lower()

            # Check if we should override existing font from lower-priority pack
            should_add = True
            if family_lower in self._fonts:
                # Check if existing fonts are from lower-priority packs
                for existing_font in self._fonts[family_lower]:
                    existing_priority = self._font_pack_priorities.get(
                        existing_font.path, -1
                    )
                    if priority <= existing_priority:
                        # This pack has same or lower priority, don't override
                        should_add = False
                        break
                # If this pack has higher priority, remove lower-priority fonts
                if should_add:
                    self._fonts[family_lower] = [
                        f
                        for f in self._fonts[family_lower]
                        if self._font_pack_priorities.get(f.path, -1) >= priority
                    ]

            if should_add:
                if family_lower not in self._fonts:
                    self._fonts[family_lower] = []
                self._fonts[family_lower].append(font_info)
                self._font_pack_priorities[font_info.path] = priority
                self._font_pack_names[font_info.path] = pack_name

    def find_font(
        self,
        family: str,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> FontInfo | None:
        """Find a font by family, weight, style, and width.

        Implements W3C CSS Fonts Level 4 matching algorithm. Returns the best
        matching font based on Manhattan Distance calculation (Family > Width >
        Style > Weight).

        Args:
            family: Font family name (case-insensitive).
            weight: Font weight (100-900, None if unspecified).
            style: Font style ("normal" or "italic").
            width: Font width/stretch (e.g., "normal", "condensed").

        Returns:
            FontInfo object containing the font path and metadata, or None
            if no matching font is found. No automatic fallback to system
            default fonts - the caller should handle fallback logic.
        """
        self.discover()

        # Step 1: Family matching with aliases
        family_lower = family.lower()
        candidates = self._fonts.get(family_lower, [])

        # Try aliases if no direct match
        if not candidates:
            candidates = try_family_aliases(family_lower, self._fonts)

        # If no candidates found, return None (no automatic fallback)
        if not candidates:
            return None

        # Step 2-4: Calculate Manhattan Distance for hierarchical matching
        best: FontInfo | None = None
        best_distance = float("inf")

        for candidate in candidates:
            distance = calculate_distance(
                target_weight=weight,
                target_style=style,
                target_width=width,
                candidate=candidate,
            )

            if distance < best_distance:
                best_distance = distance
                best = candidate

        if best is None:
            # Fallback to first candidate if no best match found
            best = candidates[0]

        return best

    def list_families(self) -> Iterator[str]:
        """List all discovered font families.

        Yields:
            Font family names (original case as stored in FontInfo).
        """
        self.discover()

        # Return unique family names (preserve original case)
        seen = set()
        for font_list in self._fonts.values():
            for font_info in font_list:
                if font_info.family not in seen:
                    seen.add(font_info.family)
                    yield font_info.family

    def get_font_path(
        self,
        family: str,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> Path | None:
        """Get path to font file.

        Args:
            family: Font family name (case-insensitive).
            weight: Font weight (100-900, None if unspecified).
            style: Font style ("normal" or "italic").
            width: Font width/stretch (e.g., "normal", "condensed").

        Returns:
            Path to font file, or None if not found.
        """
        font_info = self.find_font(family, weight, style, width)
        return font_info.path if font_info else None

    def load_font(
        self,
        font_info: FontInfo,
        size: int,
    ) -> ImageFont.FreeTypeFont | None:
        """Load a FontInfo object as a PIL ImageFont.

        This method imports PIL only when called, keeping JustMyType
        decoupled from Pillow for users who don't need it.

        Args:
            font_info: FontInfo object to load.
            size: Font size in points.

        Returns:
            PIL ImageFont object, or None if loading fails.

        Raises:
            ImportError: If Pillow is not installed.
        """
        return font_info.load(size)


# Global default registry instance
_default_registry: FontRegistry | None = None


def get_default_registry() -> FontRegistry:
    """Get the default global font registry instance.

    Returns:
        Singleton FontRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = FontRegistry()
    return _default_registry
