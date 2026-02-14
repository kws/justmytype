"""W3C CSS Fonts Level 4 matching algorithm implementation."""

from __future__ import annotations

from justmytype.types import FontInfo

# Width order for stretch distance calculation (9-point scale)
WIDTH_ORDER = [
    "ultra-condensed",
    "extra-condensed",
    "condensed",
    "semi-condensed",
    "normal",
    "semi-expanded",
    "expanded",
    "extra-expanded",
    "ultra-expanded",
]

# Known family aliases (e.g., for Linux font substitutions)
FAMILY_ALIASES: dict[str, list[str]] = {
    "arial": ["liberation sans", "dejavu sans"],
    "helvetica": ["liberation sans", "dejavu sans"],
    "times": ["liberation serif", "dejavu serif"],
    "times new roman": ["liberation serif", "dejavu serif"],
    "courier": ["liberation mono", "dejavu sans mono"],
    "courier new": ["liberation mono", "dejavu sans mono"],
}

# Platform-specific default fonts
DEFAULT_FONTS: dict[str, str] = {
    "Darwin": "SF Pro",  # San Francisco on macOS
    "Windows": "Segoe UI",
    "Linux": "DejaVu Sans",
}


def calculate_distance(
    target_weight: int | None,
    target_style: str,
    target_width: str | None,
    candidate: FontInfo,
    width_order: list[str] = WIDTH_ORDER,
) -> float:
    """Calculate Manhattan Distance for font matching.

    Implements W3C CSS Fonts Level 4 matching algorithm with hierarchy:
    Stretch (1000x) > Style (100x) > Weight (1x)

    Args:
        target_weight: Target font weight (100-900, None if unspecified).
        target_style: Target font style ("normal" or "italic").
        target_width: Target font width/stretch (e.g., "normal", "condensed").
        candidate: FontInfo candidate to score.
        width_order: Ordered list of width values for distance calculation.

    Returns:
        Distance score (lower is better). The font with the lowest distance
        is selected.
    """
    # Stretch/Width distance (highest priority: 1000x multiplier)
    stretch_dist = 0
    if target_width is not None and candidate.width is not None:
        try:
            target_idx = width_order.index(target_width)
            cand_idx = width_order.index(candidate.width)
            stretch_dist = abs(target_idx - cand_idx)
        except ValueError:
            stretch_dist = 5  # Unknown width = maximum distance
    elif target_width is not None or candidate.width is not None:
        stretch_dist = 5  # Mismatch (one specified, one not)

    # Style distance (medium priority: 100x multiplier)
    # Prefer italic > oblique > normal when italic requested
    # Prefer normal > oblique > italic when normal requested
    style_dist = 0
    if target_style == "italic":
        if candidate.style == "italic":
            style_dist = 0
        elif candidate.style == "oblique":
            style_dist = 1
        else:  # normal
            style_dist = 2
    elif target_style == "normal":
        if candidate.style == "normal":
            style_dist = 0
        elif candidate.style == "oblique":
            style_dist = 1
        else:  # italic
            style_dist = 2
    else:  # oblique or unknown
        style_dist = 0 if candidate.style == target_style else 1

    # Weight distance (lowest priority: 1x multiplier)
    # Apply CSS fallback rules for weight matching
    weight_dist = 0
    if target_weight is not None and candidate.weight is not None:
        if target_weight == candidate.weight:
            weight_dist = 0
        elif target_weight < 400:
            # Look downwards (lighter), then upwards
            if candidate.weight < target_weight:
                weight_dist = target_weight - candidate.weight
            else:
                weight_dist = (candidate.weight - target_weight) * 2  # Penalize heavier
        elif target_weight > 500:
            # Look upwards (bolder), then downwards
            if candidate.weight > target_weight:
                weight_dist = candidate.weight - target_weight
            else:
                weight_dist = (target_weight - candidate.weight) * 2  # Penalize lighter
        else:  # 400 or 500
            # Specific rules for regular/medium
            if target_weight == 400:
                # Prefer 400, then 500, then closest
                if candidate.weight == 500:
                    weight_dist = 1
                else:
                    weight_dist = abs(candidate.weight - target_weight)
            else:  # 500
                if candidate.weight == 400:
                    weight_dist = 1
                else:
                    weight_dist = abs(candidate.weight - target_weight)
        # Cap weight distance to prevent overflow
        weight_dist = min(weight_dist, 800)
    elif target_weight is not None or candidate.weight is not None:
        weight_dist = 400  # Mismatch penalty

    # Enforce hierarchy: Stretch > Style > Weight
    return (stretch_dist * 1000) + (style_dist * 100) + (weight_dist * 1)


def try_family_aliases(
    family_lower: str, available_families: dict[str, list[FontInfo]]
) -> list[FontInfo]:
    """Try to find fonts using known family aliases.

    Args:
        family_lower: Lowercase family name to find aliases for.
        available_families: Dictionary mapping lowercase family names to FontInfo lists.

    Returns:
        List of FontInfo objects from aliased families, or empty list if no matches.
    """
    aliases = FAMILY_ALIASES.get(family_lower, [])
    for alias in aliases:
        if alias in available_families:
            return available_families[alias]
    return []


def get_system_default_font(
    available_families: dict[str, list[FontInfo]], platform: str | None = None
) -> list[FontInfo]:
    """Get system default font for the platform.

    Args:
        available_families: Dictionary mapping lowercase family names to FontInfo lists.
        platform: Platform name (from platform.system()), or None to auto-detect.

    Returns:
        List of FontInfo objects for the system default font, or empty list if not found.
    """
    import platform as platform_module

    platform_name = platform or platform_module.system()
    default_font = DEFAULT_FONTS.get(platform_name, "DejaVu Sans")
    default_lower = default_font.lower()

    if default_lower in available_families:
        return available_families[default_lower]

    # Try common fallbacks
    for fallback in ["dejavu sans", "liberation sans", "arial"]:
        if fallback in available_families:
            return available_families[fallback]

    return []
