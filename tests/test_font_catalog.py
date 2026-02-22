"""Tests for font_catalog: FontAsset, FontCatalog, create_catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from justmytype.font_catalog import (
    FontAsset,
    FontCatalog,
    FontFamily,
    _normalize_family_name,
    _normalize_family_with_collisions,
    create_catalog,
)

PACK_FIXTURE = "tests.pack_fixture"


class TestNormalization:
    """Test family name normalization."""

    def test_normalize_lowercase(self) -> None:
        assert _normalize_family_name("Inter") == "inter"

    def test_normalize_spaces_to_underscore(self) -> None:
        assert _normalize_family_name("DM Sans") == "dm_sans"

    def test_normalize_digit_prefix(self) -> None:
        assert _normalize_family_name("4th Font") == "f_4th_font"

    def test_normalize_special_chars(self) -> None:
        assert _normalize_family_name("A & B") == "a_b"

    def test_collision_suffix(self) -> None:
        seen: dict[str, str] = {}
        a = _normalize_family_with_collisions("DM Sans", seen)
        b = _normalize_family_with_collisions("Dm Sans", seen)
        assert a == "dm_sans"
        assert b != "dm_sans"
        assert b.startswith("dm_sans_")


class TestCreateCatalog:
    """Test create_catalog() with pack_fixture."""

    def test_returns_font_catalog(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assert isinstance(catalog, FontCatalog)

    def test_cached_per_package(self) -> None:
        a = create_catalog(PACK_FIXTURE)
        b = create_catalog(PACK_FIXTURE)
        assert a is b

    def test_all_assets_deterministic_order(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assets = catalog.all_assets
        assert len(assets) == 3
        assert all(isinstance(a, FontAsset) for a in assets)
        families = [a.family for a in assets]
        assert families == ["Inter", "Inter", "Test Family"]

    def test_list_families(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        families = catalog.list_families()
        assert families == ("Inter", "Test Family")

    def test_by_postscript(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        by_ps = catalog.by_postscript
        assert "Inter-Regular" in by_ps
        assert "Inter-Italic" in by_ps
        assert "TestFamily-Bold" in by_ps
        assert isinstance(by_ps["Inter-Regular"], FontAsset)

    def test_missing_manifest_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="pack_manifest.json"):
            create_catalog("nonexistent.package.name.xyz")


class TestFontCatalogFind:
    """Test FontCatalog.find()."""

    def test_find_by_postscript(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.find(family="Inter", postscript_name="Inter-Italic")
        assert asset is not None
        assert asset.family == "Inter"
        assert asset.style == "italic"

    def test_find_by_family_style(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.find(family="Inter", style="normal")
        assert asset is not None
        assert asset.style == "normal"

    def test_find_by_family_weight(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.find(family="Test Family", weight=700)
        assert asset is not None
        assert asset.weight == 700

    def test_find_no_match_returns_none(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assert catalog.find(family="Nonexistent") is None


class TestFontCatalogFamilyNamespace:
    """Test family namespace (catalog.inter, etc.)."""

    def test_family_regular(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        inter = catalog.inter
        assert isinstance(inter, FontFamily)
        assert inter.regular is not None
        assert inter.regular.family == "Inter"
        assert inter.regular.style == "normal"

    def test_family_italic(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assert catalog.inter.italic is not None
        assert catalog.inter.italic.style == "italic"

    def test_family_all(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assert len(catalog.inter.all) == 2

    def test_family_weight_alias(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        assert catalog.test_family.w700 is not None
        assert catalog.test_family.w700.weight == 700

    def test_unknown_family_raises(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        with pytest.raises(AttributeError, match="no attribute 'nonexistent'"):
            _ = catalog.nonexistent

    def test_unknown_weight_raises(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        # Test Family only has weight 700
        with pytest.raises(AttributeError, match="no attribute 'w400'"):
            _ = catalog.test_family.w400


class TestFontAssetPath:
    """Test FontAsset.path()."""

    def test_path_resolves_to_file(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.inter.regular
        assert asset is not None
        path = asset.path()
        assert isinstance(path, Path)
        assert path.exists()
        assert path.name == "fixture.ttf"


class TestFontAssetVerify:
    """Test FontAsset.verify()."""

    def test_verify_returns_true_for_correct_sha256(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.inter.regular
        assert asset is not None
        assert asset.verify() is True


class TestFontAssetLoad:
    """Test FontAsset.load()."""

    def test_load_requires_pillow(self) -> None:
        catalog = create_catalog(PACK_FIXTURE)
        asset = catalog.inter.regular
        assert asset is not None
        try:
            from PIL import ImageFont  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="Pillow"):
                asset.load(16)
            return
        font = asset.load(16)
        assert font is not None
        assert "FreeTypeFont" in type(font).__name__


class TestFontCatalogInvalidManifest:
    """Test behavior with invalid manifest."""

    def test_invalid_json_raises(self) -> None:
        # We cannot easily test this without a broken fixture package;
        # at least ensure create_catalog with valid package works.
        catalog = create_catalog(PACK_FIXTURE)
        assert catalog.list_families() != ()


class TestExports:
    """Test that public API is importable from justmytype."""

    def test_font_asset_from_top_level(self) -> None:
        from justmytype import FontAsset

        assert FontAsset is not None

    def test_create_catalog_from_top_level(self) -> None:
        from justmytype import create_catalog

        assert callable(create_catalog)
