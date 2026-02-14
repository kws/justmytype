"""Tests for W3C CSS Fonts Level 4 font resolution compliance.

These tests verify that JustMyType correctly implements the W3C CSS Fonts Level 4
matching algorithm, including:
- Variable font family name registration (base name, not optical size suffixes)
- No automatic fallback (returns None when no match found)
- Family > Width > Style > Weight matching hierarchy
- CSS weight fallback rules
"""

from pathlib import Path
from unittest.mock import patch

from justmytype.core import FontRegistry
from justmytype.parser import parse_font_file
from tests.conftest import MockFontPack, create_test_font_info


class TestVariableFontFamilyName:
    """Test variable font family name registration per W3C spec.

    W3C Requirement: Variable fonts should be registered under their base family
    name (from nameID 1 or nameID 16), not with optical size suffixes like "9pt".
    In CSS, you specify font-family: "DM Sans", and the browser matches it to the
    variable font file.
    """

    def test_variable_font_uses_nameid_16_if_available(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that variable fonts prefer nameID 16 (Typographic Family Name).

        Per W3C spec, nameID 16 contains the base family name without optical size.
        """
        font_file = temp_dir / "dmsans.otf"
        font_file.touch()

        # Mock TTFont to simulate variable font with nameID 16
        mock_font = type("MockFont", (), {})()
        mock_name_table = type("MockNameTable", (), {})()
        mock_fvar = type("MockFvar", (), {})()  # Variable font has fvar table

        def mock_get(name: str):
            if name == "name":
                return mock_name_table
            if name == "fvar":
                return mock_fvar
            return None

        mock_font.get = mock_get

        # nameID 16 returns base name, nameID 1 returns name with optical size
        def mock_get_debug_name(name_id: int) -> str | None:
            if name_id == 16:
                return "DM Sans"  # Typographic Family Name (base name)
            if name_id == 1:
                return "DM Sans 9pt"  # Family name with optical size
            if name_id == 6:
                return "DMSans-Regular"
            if name_id == 2:
                return "Regular"
            return None

        mock_name_table.getDebugName = mock_get_debug_name

        with patch("justmytype.parser.TTFont", return_value=mock_font):
            result = parse_font_file(font_file)

        assert result is not None
        assert result.family == "DM Sans"  # Should use base name, not "DM Sans 9pt"

    def test_variable_font_strips_optical_size_from_nameid_1(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that variable fonts strip optical size patterns from nameID 1.

        If nameID 16 is not available, fallback to nameID 1 and strip patterns
        like " 9pt", " 10pt", " 12.5pt".
        """
        font_file = temp_dir / "dmsans.otf"
        font_file.touch()

        # Mock TTFont to simulate variable font without nameID 16
        mock_font = type("MockFont", (), {})()
        mock_name_table = type("MockNameTable", (), {})()
        mock_fvar = type("MockFvar", (), {})()  # Variable font has fvar table

        def mock_get(name: str):
            if name == "name":
                return mock_name_table
            if name == "fvar":
                return mock_fvar
            return None

        mock_font.get = mock_get

        # nameID 16 not available, nameID 1 has optical size
        def mock_get_debug_name(name_id: int) -> str | None:
            if name_id == 16:
                return None  # Typographic Family Name not available
            if name_id == 1:
                return "DM Sans 9pt"  # Family name with optical size
            if name_id == 6:
                return "DMSans-Regular"
            if name_id == 2:
                return "Regular"
            return None

        mock_name_table.getDebugName = mock_get_debug_name

        with patch("justmytype.parser.TTFont", return_value=mock_font):
            result = parse_font_file(font_file)

        assert result is not None
        assert result.family == "DM Sans"  # Should strip " 9pt" suffix

    def test_variable_font_strips_various_optical_size_patterns(
        self, temp_dir: Path
    ) -> None:
        """Test that various optical size patterns are stripped correctly."""
        test_cases = [
            ("DM Sans 9pt", "DM Sans"),
            ("DM Sans 10pt", "DM Sans"),
            ("DM Sans 12.5pt", "DM Sans"),
            ("Roboto 8pt", "Roboto"),
            ("Inter 11pt", "Inter"),
        ]

        for input_name, expected_base in test_cases:
            font_file = temp_dir / "test.otf"
            font_file.touch()

            mock_font = type("MockFont", (), {})()
            mock_name_table = type("MockNameTable", (), {})()
            mock_fvar = type("MockFvar", (), {})()

            def mock_get(name: str, name_table=mock_name_table, fvar=mock_fvar):
                if name == "name":
                    return name_table
                if name == "fvar":
                    return fvar
                return None

            mock_font.get = mock_get

            def mock_get_debug_name(name_id: int, font_name=input_name) -> str | None:
                if name_id == 16:
                    return None
                if name_id == 1:
                    return font_name
                if name_id == 6:
                    return "Test-Regular"
                if name_id == 2:
                    return "Regular"
                return None

            mock_name_table.getDebugName = mock_get_debug_name

            with patch("justmytype.parser.TTFont", return_value=mock_font):
                result = parse_font_file(font_file)

            assert result is not None
            assert (
                result.family == expected_base
            ), f"Failed to strip optical size from '{input_name}'"

    def test_variable_font_regex_robustness_edge_cases(self, temp_dir: Path) -> None:
        """Test regex robustness for edge cases in variable font name parsing.

        W3C Compliance: Handle malformed or edge patterns that real-world fonts
        sometimes have, including:
        - Space between number and pt ("12 pt")
        - Non-numeric suffixes that might be confused with optical size
        - Regression test for fonts ending in 'pt' (e.g., "Concept")
        """
        # Edge case test cases: (input_name, expected_output, description)
        test_cases = [
            # Standard cases (already covered, but included for completeness)
            ("DM Sans 9pt", "DM Sans", "Standard pattern"),
            ("DM Sans 12.5pt", "DM Sans", "Decimal pattern"),
            # Edge case: Space between number and pt
            (
                "DM Sans 12 pt",
                "DM Sans 12 pt",
                "Space before pt - should NOT strip (not matched by regex)",
            ),
            # Edge case: Non-numeric suffix (should not be stripped)
            (
                "DM Sans Display",
                "DM Sans Display",
                "Non-numeric suffix - should NOT strip",
            ),
            # Regression test: Font name ending in 'pt' (should not strip incorrectly)
            ("Concept", "Concept", "Font ending in 'pt' - should remain unchanged"),
            (
                "Concept pt",
                "Concept pt",
                "Font with 'pt' not as optical size - should remain unchanged",
            ),
            # Edge case: Multiple spaces
            ("DM Sans  9pt", "DM Sans", "Multiple spaces before pt"),
            # Edge case: Trailing whitespace
            ("DM Sans 9pt ", "DM Sans", "Trailing whitespace"),
        ]

        for input_name, expected_output, description in test_cases:
            font_file = temp_dir / f"test_{hash(input_name)}.otf"
            font_file.touch()

            mock_font = type("MockFont", (), {})()
            mock_name_table = type("MockNameTable", (), {})()
            mock_fvar = type("MockFvar", (), {})()

            def mock_get(name: str, name_table=mock_name_table, fvar=mock_fvar):
                if name == "name":
                    return name_table
                if name == "fvar":
                    return fvar
                return None

            mock_font.get = mock_get

            def mock_get_debug_name(name_id: int, font_name=input_name) -> str | None:
                if name_id == 16:
                    return None
                if name_id == 1:
                    return font_name
                if name_id == 6:
                    return "Test-Regular"
                if name_id == 2:
                    return "Regular"
                return None

            mock_name_table.getDebugName = mock_get_debug_name

            with patch("justmytype.parser.TTFont", return_value=mock_font):
                result = parse_font_file(font_file)

            assert (
                result is not None
            ), f"Failed to parse font for '{input_name}' ({description})"
            assert (
                result.family == expected_output
            ), f"Failed for '{input_name}' ({description}): expected '{expected_output}', got '{result.family}'"

    def test_non_variable_font_uses_nameid_1_as_before(self, temp_dir: Path) -> None:
        """Test that non-variable fonts continue to use nameID 1 unchanged."""
        font_file = temp_dir / "regular.otf"
        font_file.touch()

        mock_font = type("MockFont", (), {})()
        mock_name_table = type("MockNameTable", (), {})()

        def mock_get(name: str):
            if name == "name":
                return mock_name_table
            if name == "fvar":
                return None  # Not a variable font
            return None

        mock_font.get = mock_get

        def mock_get_debug_name(name_id: int) -> str | None:
            if name_id == 1:
                return "Arial"  # Should be used as-is for non-variable fonts
            if name_id == 6:
                return "Arial-Regular"
            if name_id == 2:
                return "Regular"
            return None

        mock_name_table.getDebugName = mock_get_debug_name

        with patch("justmytype.parser.TTFont", return_value=mock_font):
            result = parse_font_file(font_file)

        assert result is not None
        assert result.family == "Arial"  # Should use nameID 1 unchanged


class TestNoAutomaticFallback:
    """Test that find_font() returns None when no match is found.

    W3C Requirement: The spec says fallback should occur only after exhausting
    alternatives in the specified family. For a library API, find_font() should
    return None when no match is found, letting the caller handle fallback.
    """

    def test_find_font_returns_none_for_nonexistent_font(
        self, empty_font_registry: FontRegistry
    ) -> None:
        """Test that find_font() returns None for nonexistent fonts."""
        result = empty_font_registry.find_font("NonexistentFont12345")
        assert result is None

    def test_find_font_no_system_default_fallback(
        self, empty_font_registry: FontRegistry
    ) -> None:
        """Test that find_font() does not fallback to system default font."""
        # Even with system fonts available, nonexistent font should return None
        empty_font_registry.discover()
        result = empty_font_registry.find_font("NonexistentFont12345")
        assert result is None


class TestW3CMatchingHierarchy:
    """Test W3C CSS Fonts Level 4 matching hierarchy.

    W3C Requirement: Matching follows strict hierarchy:
    Family > Width (Stretch) > Style > Weight
    """

    def test_family_match_has_highest_priority(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that family matching is checked first (highest priority)."""
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Font with matching family but different attributes
            mock_parse.return_value = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="normal"
            )

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Should find Arial even if other attributes don't match exactly
                    result = font_registry.find_font(
                        "Arial", weight=700, style="italic"
                    )
                    assert result is not None
                    assert result.family == "Arial"

    def test_width_matching_priority_over_style_and_weight(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that width matching has priority over style and weight.

        W3C Requirement: Width (Stretch) > Style > Weight
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Font with matching width but different style/weight
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="condensed"
            )
            # Font with matching style/weight but different width
            font2 = create_test_font_info(
                font_file2, "Arial", weight=700, style="italic", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request: weight=700, style=italic, width=condensed
                    # Should prefer font1 (matching width) over font2 (matching style/weight)
                    result = font_registry.find_font(
                        "Arial", weight=700, style="italic", width="condensed"
                    )
                    assert result is not None
                    # Width has priority, so should get condensed font
                    assert result.width == "condensed"

    def test_style_matching_priority_over_weight(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that style matching has priority over weight.

        W3C Requirement: Style > Weight
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Font with matching style but different weight
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="italic", width="normal"
            )
            # Font with matching weight but different style
            font2 = create_test_font_info(
                font_file2, "Arial", weight=700, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request: weight=700, style=italic
                    # Should prefer font1 (matching style) over font2 (matching weight)
                    result = font_registry.find_font(
                        "Arial", weight=700, style="italic"
                    )
                    assert result is not None
                    assert result.style == "italic"  # Style has priority


class TestW3CWeightFallback:
    """Test W3C CSS weight fallback rules.

    W3C Requirement: CSS weight fallback follows specific rules:
    - Target < 400: Look downwards (lighter), then upwards
    - Target > 500: Look upwards (bolder), then downwards
    - Target 400 or 500: Specific rules for snapping to regular/medium
    """

    def test_weight_fallback_for_lighter_target(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test weight fallback for targets < 400 (prefer lighter, then heavier).

        W3C Requirement: For target < 400, look downwards (lighter) first,
        then upwards (heavier).
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Lighter font (preferred for target 300)
            font1 = create_test_font_info(
                font_file1, "Arial", weight=200, style="normal", width="normal"
            )
            # Heavier font (penalized for target 300)
            font2 = create_test_font_info(
                font_file2, "Arial", weight=400, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request weight=300, should prefer lighter (200) over heavier (400)
                    result = font_registry.find_font("Arial", weight=300)
                    assert result is not None
                    assert result.weight == 200  # Lighter is preferred

    def test_weight_fallback_for_bolder_target(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test weight fallback for targets > 500 (prefer bolder, then lighter).

        W3C Requirement: For target > 500, look upwards (bolder) first,
        then downwards (lighter).
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Bolder font (preferred for target 700)
            font1 = create_test_font_info(
                font_file1, "Arial", weight=800, style="normal", width="normal"
            )
            # Lighter font (penalized for target 700)
            font2 = create_test_font_info(
                font_file2, "Arial", weight=600, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request weight=700, should prefer bolder (800) over lighter (600)
                    result = font_registry.find_font("Arial", weight=700)
                    assert result is not None
                    assert result.weight == 800  # Bolder is preferred

    def test_weight_fallback_for_regular_target(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test weight fallback for target 400 (prefer 400, then 500).

        W3C Requirement: For target 400, prefer 400, then 500, then closest.
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Exact match (preferred)
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="normal"
            )
            # 500 (second choice for target 400)
            font2 = create_test_font_info(
                font_file2, "Arial", weight=500, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request weight=400, should prefer exact match (400)
                    result = font_registry.find_font("Arial", weight=400)
                    assert result is not None
                    assert result.weight == 400  # Exact match is preferred

    def test_weight_fallback_for_medium_target(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test weight fallback for target 500 (prefer 400, then 600+).

        W3C Requirement: For target 500, the spec has a specific rule:
        look at 400 first, then 600+. This is the "400/500 snap rule" where
        400 and 500 are treated specially.
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # 400 (preferred for target 500 per W3C spec)
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="normal"
            )
            # 600 (should be second choice for target 500)
            font2 = create_test_font_info(
                font_file2, "Arial", weight=600, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request weight=500, should prefer 400 over 600 per W3C 400/500 snap rule
                    result = font_registry.find_font("Arial", weight=500)
                    assert result is not None
                    assert (
                        result.weight == 400
                    )  # 400 is preferred over 600 for target 500


class TestW3CStyleMatching:
    """Test W3C CSS style matching rules.

    W3C Requirement:
    - If italic requested: Prefer italic > oblique > normal
    - If normal requested: Prefer normal > oblique > italic
    """

    def test_italic_request_prefers_italic_over_oblique_over_normal(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that italic request prefers italic > oblique > normal."""
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file3 = temp_dir / "font3.ttf"
        font_file1.touch()
        font_file2.touch()
        font_file3.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="italic", width="normal"
            )
            font2 = create_test_font_info(
                font_file2, "Arial", weight=400, style="oblique", width="normal"
            )
            font3 = create_test_font_info(
                font_file3, "Arial", weight=400, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                if path == font_file2:
                    return font2
                return font3

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2, font_file3]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request italic, should prefer italic > oblique > normal
                    result = font_registry.find_font("Arial", style="italic")
                    assert result is not None
                    assert result.style == "italic"  # Italic is preferred

    def test_normal_request_prefers_normal_over_oblique_over_italic(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that normal request prefers normal > oblique > italic."""
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file3 = temp_dir / "font3.ttf"
        font_file1.touch()
        font_file2.touch()
        font_file3.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="normal"
            )
            font2 = create_test_font_info(
                font_file2, "Arial", weight=400, style="oblique", width="normal"
            )
            font3 = create_test_font_info(
                font_file3, "Arial", weight=400, style="italic", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                if path == font_file2:
                    return font2
                return font3

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2, font_file3]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request normal, should prefer normal > oblique > italic
                    result = font_registry.find_font("Arial", style="normal")
                    assert result is not None
                    assert result.style == "normal"  # Normal is preferred

    def test_oblique_request_fallback_behavior(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test oblique request fallback behavior.

        W3C Requirement: If oblique is requested, the spec says to treat it
        similar to italic in most modern contexts, or strictly:
        Oblique > Italic > Normal (when oblique is explicitly requested).
        """
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file3 = temp_dir / "font3.ttf"
        font_file1.touch()
        font_file2.touch()
        font_file3.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="oblique", width="normal"
            )
            font2 = create_test_font_info(
                font_file2, "Arial", weight=400, style="italic", width="normal"
            )
            font3 = create_test_font_info(
                font_file3, "Arial", weight=400, style="normal", width="normal"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                if path == font_file2:
                    return font2
                return font3

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2, font_file3]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request oblique, should prefer oblique > italic > normal
                    result = font_registry.find_font("Arial", style="oblique")
                    assert result is not None
                    assert (
                        result.style == "oblique"
                    )  # Oblique is preferred when explicitly requested


class TestW3CWidthMatching:
    """Test W3C CSS width/stretch matching.

    W3C Requirement: Uses 9-point width scale with closest match:
    ultra-condensed, extra-condensed, condensed, semi-condensed, normal,
    semi-expanded, expanded, extra-expanded, ultra-expanded
    """

    def test_width_matching_finds_closest_match(
        self, temp_dir: Path, font_registry: FontRegistry
    ) -> None:
        """Test that width matching finds the closest match on 9-point scale."""
        font_file1 = temp_dir / "font1.ttf"
        font_file2 = temp_dir / "font2.ttf"
        font_file1.touch()
        font_file2.touch()

        with patch("justmytype.core.parse_font_file") as mock_parse:
            # Closer to condensed (semi-condensed)
            font1 = create_test_font_info(
                font_file1, "Arial", weight=400, style="normal", width="semi-condensed"
            )
            # Farther from condensed (expanded)
            font2 = create_test_font_info(
                font_file2, "Arial", weight=400, style="normal", width="expanded"
            )

            def mock_parse_side_effect(path: Path):
                if path == font_file1:
                    return font1
                return font2

            mock_parse.side_effect = mock_parse_side_effect

            with patch("justmytype.core.find_font_files") as mock_find:
                mock_find.return_value = [font_file1, font_file2]

                pack = MockFontPack([temp_dir], priority=100, name="test-pack")

                with patch.object(
                    font_registry,
                    "_get_entry_points",
                    return_value=[("test-pack", pack)],
                ):
                    font_registry.discover()

                    # Request condensed, should prefer semi-condensed (closer) over expanded
                    result = font_registry.find_font("Arial", width="condensed")
                    assert result is not None
                    assert result.width == "semi-condensed"  # Closer match
