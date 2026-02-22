"""Font catalog: manifest-backed FontInfo and create_catalog for pack-based font access."""

from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from justmytype.types import FontInfo

# Cache for as_file() context managers so resolved paths stay valid for zipped packages
_path_cache: dict[tuple[str, str], tuple[Path, Any]] = {}


def _resolve_resource_path(package: str, relative_path: str) -> Path:
    """Resolve a package-relative font path to a filesystem Path.

    Uses importlib.resources; for zipped packages the resource is extracted
    to a temporary location (cached for the process).
    """
    key = (package, relative_path)
    if key in _path_cache:
        return _path_cache[key][0]
    traversable = files(package) / "fonts" / relative_path
    if not traversable.is_file():
        raise FileNotFoundError(
            f"Font resource not found: fonts/{relative_path} in {package}"
        )
    try:
        cm = as_file(traversable)
        p = cm.__enter__()
        _path_cache[key] = (Path(p), cm)
        return Path(p)
    except Exception:
        raise FileNotFoundError(
            f"Could not resolve font: fonts/{relative_path} in {package}"
        ) from None


def _normalize_family_name(family: str) -> str:
    """Convert family display name to a stable Python identifier (no collision handling)."""
    s = family.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if s and s[0].isdigit():
        s = "f_" + s
    return s or "unknown"


def _normalize_family_with_collisions(family: str, seen: dict[str, str]) -> str:
    """Return unique Python identifier for family; append hash suffix on collision."""
    base = _normalize_family_name(family)
    if base not in seen:
        seen[base] = family
        return base
    if seen[base] == family:
        return base
    suffix = hashlib.sha256(family.encode()).hexdigest()[:4]
    candidate = f"{base}_{suffix}"
    while candidate in seen and seen[candidate] != family:
        suffix = hashlib.sha256((family + candidate).encode()).hexdigest()[:4]
        candidate = f"{base}_{suffix}"
    seen[candidate] = family
    return candidate


class FontFamily:
    """Namespace for one font family: .regular, .italic, .all, .w400, etc."""

    __slots__ = ("_assets", "_by_weight")

    def __init__(self, assets: tuple[FontInfo, ...]) -> None:
        self._assets = assets
        self._by_weight: dict[int, FontInfo] = {}
        for a in assets:
            if a.weight is not None:
                self._by_weight.setdefault(a.weight, a)

    def _best_for_style(self, style: str) -> FontInfo | None:
        """First asset for style, preferring weight 400."""
        for a in self._assets:
            if a.style == style and a.weight == 400:
                return a
        for a in self._assets:
            if a.style == style:
                return a
        return None

    @property
    def regular(self) -> FontInfo | None:
        """First normal-style asset, preferring weight 400."""
        return self._best_for_style("normal")

    @property
    def italic(self) -> FontInfo | None:
        """First italic-style asset, preferring weight 400."""
        return self._best_for_style("italic")

    @property
    def all(self) -> tuple[FontInfo, ...]:
        """All assets for this family."""
        return self._assets

    def __repr__(self) -> str:
        name = self._assets[0].family if self._assets else "?"
        return f"FontFamily({name!r}, {len(self._assets)} assets)"

    def __getattr__(self, name: str) -> FontInfo:
        if name.startswith("w") and name[1:].isdigit():
            w = int(name[1:])
            if w in self._by_weight:
                return self._by_weight[w]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )


class FontCatalog:
    """Catalog of FontInfo from a pack manifest; family namespaces via __getattr__."""

    __slots__ = ("_assets", "_by_postscript", "_families", "_by_normalized")

    def __init__(
        self,
        assets: tuple[FontInfo, ...],
        by_postscript: dict[str, FontInfo],
        families: tuple[str, ...],
        by_normalized: dict[str, FontFamily],
    ) -> None:
        self._assets = assets
        self._by_postscript = by_postscript
        self._families = families
        self._by_normalized = by_normalized

    @property
    def all_assets(self) -> tuple[FontInfo, ...]:
        """All font assets in deterministic order."""
        return self._assets

    @property
    def by_postscript(self) -> dict[str, FontInfo]:
        """Map PostScript name to FontInfo (only entries with postscript_name)."""
        return self._by_postscript

    def list_families(self) -> tuple[str, ...]:
        """Unique family names in manifest order."""
        return self._families

    def __repr__(self) -> str:
        return (
            f"FontCatalog({len(self._families)} families, {len(self._assets)} assets)"
        )

    def find(
        self,
        *,
        family: str,
        style: str | None = None,
        weight: int | None = None,
        postscript_name: str | None = None,
    ) -> FontInfo | None:
        """Return one FontInfo matching the criteria; exact family match required."""
        if postscript_name is not None and postscript_name in self._by_postscript:
            return self._by_postscript[postscript_name]
        candidates = [a for a in self._assets if a.family == family]
        if not candidates:
            return None
        if style is not None:
            candidates = [a for a in candidates if a.style == style]
        if weight is not None:
            candidates = [a for a in candidates if a.weight == weight]
        if not candidates:
            return None
        # Deterministic: prefer normal, then weight 400, then path
        candidates.sort(
            key=lambda a: (
                0 if a.style == "normal" else 1,
                (a.weight if a.weight is not None else -1),
                str(a.path),
            )
        )
        return candidates[0]

    def __getattr__(self, name: str) -> FontFamily:
        if name in self._by_normalized:
            return self._by_normalized[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )


_catalog_cache: dict[str, FontCatalog] = {}


def create_catalog(package: str) -> FontCatalog:
    """Build a FontCatalog from pack_manifest.json in the given package's fonts dir.

    Result is cached per package name. The manifest must live at
    <package>/fonts/pack_manifest.json (resource path).
    """
    if package in _catalog_cache:
        return _catalog_cache[package]
    try:
        manifest_traversable = files(package) / "fonts" / "pack_manifest.json"
        data = manifest_traversable.read_bytes()
    except Exception as e:
        raise FileNotFoundError(
            f"pack_manifest.json not found for package {package}"
        ) from e
    try:
        manifest = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid pack_manifest.json in {package}") from e
    font_entries = manifest.get("fonts") or []
    assets_list: list[FontInfo] = []
    for entry in font_entries:
        if not isinstance(entry, dict):
            continue
        path_str = (entry.get("path") or "").replace("\\", "/")
        if not path_str:
            continue
        resolved_path = _resolve_resource_path(package, path_str)
        sha256_val = entry.get("sha256")
        assets_list.append(
            FontInfo(
                path=resolved_path,
                family=entry.get("family") or "",
                style=entry.get("style") or "normal",
                weight=entry.get("weight"),
                width=entry.get("width"),
                postscript_name=entry.get("postscript_name"),
                variant=entry.get("variant"),
                sha256=sha256_val if sha256_val else None,
            )
        )
    # Deterministic order
    assets_list.sort(
        key=lambda a: (
            a.family,
            a.style,
            a.weight if a.weight is not None else -1,
            a.postscript_name or "",
            str(a.path),
        )
    )
    assets = tuple(assets_list)
    by_postscript: dict[str, FontInfo] = {}
    for a in assets:
        if a.postscript_name:
            by_postscript[a.postscript_name] = a
    # Unique families in order of first appearance
    seen_family: set[str] = set()
    families_list: list[str] = []
    for a in assets:
        if a.family and a.family not in seen_family:
            seen_family.add(a.family)
            families_list.append(a.family)
    families = tuple(families_list)
    # Family -> assets
    by_family: dict[str, list[FontInfo]] = {}
    for a in assets:
        if a.family:
            by_family.setdefault(a.family, []).append(a)
    # Normalized name -> FontFamily (with collision handling)
    seen_norm: dict[str, str] = {}
    by_normalized: dict[str, FontFamily] = {}
    for fam in families_list:
        norm = _normalize_family_with_collisions(fam, seen_norm)
        by_normalized[norm] = FontFamily(tuple(by_family[fam]))
    catalog = FontCatalog(
        assets=assets,
        by_postscript=by_postscript,
        families=families,
        by_normalized=by_normalized,
    )
    _catalog_cache[package] = catalog
    return catalog
