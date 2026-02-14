"""Tests for font matching algorithm."""

from pathlib import Path

import pytest

from justmytype.matcher import (
    calculate_distance,
    get_system_default_font,
    try_family_aliases,
)
from justmytype.types import FontInfo


def test_calculate_distance_exact_match() -> None:
    """Test distance calculation for exact match."""
    candidate = FontInfo(
        path=Path("/test/font.ttf"),
        family="Test",
        weight=400,
        style="normal",
        width="normal",
    )

    distance = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate,
    )

    assert distance == 0.0


def test_calculate_distance_weight_difference() -> None:
    """Test distance calculation with weight difference."""
    candidate = FontInfo(
        path=Path("/test/font.ttf"),
        family="Test",
        weight=700,
        style="normal",
        width="normal",
    )

    distance = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate,
    )

    # Should have weight distance (300 * 2 = 600 for lighter target)
    assert distance > 0
    assert distance < 1000  # Less than style distance


def test_calculate_distance_style_difference() -> None:
    """Test distance calculation with style difference."""
    candidate = FontInfo(
        path=Path("/test/font.ttf"),
        family="Test",
        weight=400,
        style="italic",
        width="normal",
    )

    distance = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate,
    )

    # Style distance should be 200 (2 * 100)
    assert distance == 200.0


def test_calculate_distance_width_difference() -> None:
    """Test distance calculation with width difference."""
    candidate = FontInfo(
        path=Path("/test/font.ttf"),
        family="Test",
        weight=400,
        style="normal",
        width="condensed",
    )

    distance = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate,
    )

    # Width distance should be 2000 (2 * 1000)
    assert distance == 2000.0


def test_calculate_distance_hierarchy() -> None:
    """Test that width > style > weight hierarchy is enforced."""
    # Width difference should dominate
    candidate1 = FontInfo(
        path=Path("/test/font1.ttf"),
        family="Test",
        weight=400,
        style="normal",
        width="condensed",  # Different width
    )

    # Style difference should be less than width
    candidate2 = FontInfo(
        path=Path("/test/font2.ttf"),
        family="Test",
        weight=400,
        style="italic",  # Different style
        width="normal",
    )

    distance1 = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate1,
    )

    distance2 = calculate_distance(
        target_weight=400,
        target_style="normal",
        target_width="normal",
        candidate=candidate2,
    )

    # Width difference should be much larger than style difference
    assert distance1 > distance2


def test_calculate_distance_weight_fallback_lighter() -> None:
    """Test weight fallback for lighter targets (< 400)."""
    # Target is 300, candidate is 200 (lighter, preferred)
    candidate1 = FontInfo(
        path=Path("/test/font1.ttf"),
        family="Test",
        weight=200,
        style="normal",
        width="normal",
    )

    # Target is 300, candidate is 400 (heavier, penalized)
    candidate2 = FontInfo(
        path=Path("/test/font2.ttf"),
        family="Test",
        weight=400,
        style="normal",
        width="normal",
    )

    distance1 = calculate_distance(
        target_weight=300,
        target_style="normal",
        target_width="normal",
        candidate=candidate1,
    )

    distance2 = calculate_distance(
        target_weight=300,
        target_style="normal",
        target_width="normal",
        candidate=candidate2,
    )

    # Lighter should be preferred (lower distance)
    assert distance1 < distance2


def test_calculate_distance_weight_fallback_bolder() -> None:
    """Test weight fallback for bolder targets (> 500)."""
    # Target is 700, candidate is 800 (bolder, preferred)
    candidate1 = FontInfo(
        path=Path("/test/font1.ttf"),
        family="Test",
        weight=800,
        style="normal",
        width="normal",
    )

    # Target is 700, candidate is 600 (lighter, penalized)
    candidate2 = FontInfo(
        path=Path("/test/font2.ttf"),
        family="Test",
        weight=600,
        style="normal",
        width="normal",
    )

    distance1 = calculate_distance(
        target_weight=700,
        target_style="normal",
        target_width="normal",
        candidate=candidate1,
    )

    distance2 = calculate_distance(
        target_weight=700,
        target_style="normal",
        target_width="normal",
        candidate=candidate2,
    )

    # Bolder should be preferred (lower distance)
    assert distance1 < distance2


def test_try_family_aliases() -> None:
    """Test family alias matching."""
    available_families = {
        "liberation sans": [
            FontInfo(path=Path("/test/liberation.ttf"), family="Liberation Sans")
        ],
        "dejavu sans": [
            FontInfo(path=Path("/test/dejavu.ttf"), family="DejaVu Sans")
        ],
    }

    # Arial should match Liberation Sans
    result = try_family_aliases("arial", available_families)
    assert len(result) > 0
    assert result[0].family == "Liberation Sans"


def test_try_family_aliases_no_match() -> None:
    """Test family alias matching with no matches."""
    available_families = {
        "other font": [
            FontInfo(path=Path("/test/other.ttf"), family="Other Font")
        ],
    }

    result = try_family_aliases("arial", available_families)
    assert len(result) == 0


def test_get_system_default_font() -> None:
    """Test getting system default font."""
    available_families = {
        "dejavu sans": [
            FontInfo(path=Path("/test/dejavu.ttf"), family="DejaVu Sans")
        ],
    }

    result = get_system_default_font(available_families, "Linux")
    assert len(result) > 0
    assert result[0].family == "DejaVu Sans"


def test_get_system_default_font_fallback() -> None:
    """Test system default font fallback."""
    available_families = {
        "liberation sans": [
            FontInfo(path=Path("/test/liberation.ttf"), family="Liberation Sans")
        ],
    }

    result = get_system_default_font(available_families, "Linux")
    # Should fall back to Liberation Sans
    assert len(result) > 0

