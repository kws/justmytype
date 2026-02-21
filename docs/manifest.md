# Font Pack Manifest

This document describes the optional **font pack manifest**: a JSON file (`pack_manifest.json`) that font packs may ship alongside their font files. It provides reproducibility, provenance, and optional runtime metadata. The manifest is **optional**; font discovery works by scanning directories whether or not a manifest is present.

## 1. Rationale

### Why font packs have a manifest

- **Reproducibility**: A single source of truth for the upstream ref (e.g. git commit SHA) and archive checksum. Rebuilds can verify they use the same sources.
- **Provenance**: Clear record of where the fonts came from (repo, ref), which families are included, and which licenses apply.
- **Optional runtime metadata**: Tools (including justmytype) can expose pack version, upstream ref, and family list without scanning font files. Useful for "list packs" or "pack info" features.

### Relationship to JustMyResource

The idea aligns with [JustMyResource](https://github.com/kws/justmyresource)'s `pack_manifest.json` for icon packs: same filename and similar role (build-time artifact, optional runtime read). The font manifest uses font-specific fields (e.g. per-font metadata from fonttools, family paths from upstream).

### Design principles

- **Precision**: Font metadata (family, weight, style, width, postscript name) in the manifest comes from fonttools at build time, not from filename heuristics.
- **Optional for runtime**: Discovery and `find_font()` remain driven by directory scanning. The manifest is supplementary metadata only.

## 2. Schema

### manifest_version

- **Type**: string
- **Required**: yes
- **Description**: Schema version for forward compatibility (e.g. `"1.0"`). Readers should ignore manifests with unknown versions or handle them conservatively.

### pack

- **Type**: object
- **Required**: yes
- **Fields**:
  - `name` (string, required): Stable pack identifier (e.g. `justmytype-western-core`). Should match the pack's `get_name()`.
  - `version` (string, required): Pack or upstream version string.
  - `entry_point` (string, required): Entry point name under `justmytype.packs`.
  - `priority` (integer, required): Pack priority (e.g. 100 for user/bundled packs).
  - `description` (string, optional): Human-readable description.
  - `source_url` (string, optional): URL to pack or upstream project.

### source

- **Type**: object
- **Required**: yes
- **Fields**:
  - `repo` (string, required): Upstream repository URL (e.g. `https://github.com/google/fonts`).
  - `ref` (string, required): Git ref used (commit SHA preferred for reproducibility).
  - `archive_sha256` (string, optional): SHA-256 of the downloaded archive.

### build

- **Type**: object
- **Required**: yes
- **Fields**:
  - `timestamp` (string, required): UTC ISO 8601 build timestamp.
  - `tool_version` (string, optional): Version of the pack-tools that produced the manifest.

### families

- **Type**: array of strings
- **Required**: yes
- **Description**: Logical family paths from upstream (e.g. `["ofl/inter", "ofl/notosans"]`). Used for provenance and optional "list families" without scanning.

### fonts

- **Type**: array of objects
- **Required**: yes
- **Description**: Per-file inventory. Enables integrity checks and "list fonts in this pack" without scanning. Each entry must be derived from fonttools at build time (no filename guessing).
- **Per-entry fields**:
  - `path` (string, required): Path relative to the pack font root.
  - `sha256` (string, required): SHA-256 of the font file.
  - `family` (string, required): Font family name from name table.
  - `style` (string, required): `"normal"` or `"italic"`.
  - `weight` (integer or null): CSS weight 100–900, or null if unknown.
  - `width` (string or null): e.g. `"normal"`, `"condensed"`, or null.
  - `postscript_name` (string or null): PostScript name if available.

### licenses

- **Type**: array of objects
- **Required**: yes
- **Per-entry fields**:
  - `spdx` (string, required): SPDX license identifier.
  - `path` (string, required): Path to the license file within the pack.

### Optional / recommended top-level fields

- `family_count` (integer): Number of distinct families.
- `font_file_count` (integer): Number of font files.
- `justmytype_min` (string): Minimum justmytype version the pack is intended to work with.

## 3. Lifecycle

- **Who writes it**: Pack build tooling (e.g. justmytype_essentials pack-tools) during `build pack`, after copying font families from the upstream cache into the pack.
- **Who may read it**: Pack-tools (validation), justmytype (optional metadata for list-packs / pack info), humans and other tooling.

## 4. Relationship to JustMyType

Font packs are discovered via the `justmytype.packs` Entry Point; each pack implements the `FontPack` protocol (`get_font_directories`, `get_priority`, `get_name`). The manifest is **not** required for discovery. If present, justmytype may optionally read it to expose pack version, upstream ref, and family list without scanning. See [architecture.md](architecture.md#46-font-pack-manifest-optional) for the optional manifest support contract.

## 5. Example (minimal)

```json
{
  "manifest_version": "1.0",
  "pack": {
    "name": "justmytype-western-core",
    "version": "0.1.0",
    "entry_point": "western-core",
    "priority": 100,
    "description": "Western core fonts: Inter, Noto Sans, Source Serif 4, etc."
  },
  "source": {
    "repo": "https://github.com/google/fonts",
    "ref": "a1b2c3d4e5f6...",
    "archive_sha256": "..."
  },
  "build": {
    "timestamp": "2026-02-21T18:00:00Z",
    "tool_version": "0.1.0"
  },
  "families": ["ofl/inter", "ofl/notosans"],
  "fonts": [
    {
      "path": "ofl/inter/Inter-Regular.ttf",
      "sha256": "...",
      "family": "Inter",
      "style": "normal",
      "weight": 400,
      "width": "normal",
      "postscript_name": "Inter-Regular"
    }
  ],
  "licenses": [
    { "spdx": "OFL-1.1", "path": "LICENSES/OFL-1.1.txt" }
  ]
}
```
