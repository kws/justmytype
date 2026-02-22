# JustMyType

A precise, lightweight, and extensible font discovery library for Python. JustMyType provides a robust "Font Atlas" for the Python ecosystem—a definitive map of every font available to an application, whether installed on the system or bundled in a Python package.

## Features

- **Cross-platform**: Unified API across macOS, Linux, and Windows
- **Extensible**: Font packs can be added via standard Python EntryPoints mechanism
- **Efficient**: Lazy discovery with in-memory caching
- **Flexible**: Supports font matching by family, weight, style, and width with intelligent fallback
- **W3C Compliant**: Implements CSS Fonts Level 4 matching algorithm for browser-like behavior
- **Precise**: Uses `fonttools` to parse binary font tables—never guesses from filenames

## Installation

```bash
pip install justmytype
```

For Pillow support (optional, for loading fonts):

```bash
pip install justmytype[pillow]
```

## Quick Start

```python
from justmytype import FontRegistry, get_default_registry

# Get default registry
registry = get_default_registry()

# Find a font (lazy discovery happens automatically)
font_info = registry.find_font("Arial", weight=700, style="normal")
if font_info:
    # Load as PIL ImageFont (requires Pillow)
    font = font_info.load(size=16)

    # Or use the path directly
    print(f"Found font at: {font_info.path}")
```

## Basic Usage

### Finding Fonts

```python
from justmytype import FontRegistry

registry = FontRegistry()

# Find by family name
font_info = registry.find_font("Roboto", weight=400)

# Find with style
font_info = registry.find_font("Open Sans", weight=700, style="italic")

# Find with width
font_info = registry.find_font("Arial", width="condensed")

# List all available families
for family in registry.list_families():
    print(family)
```

### Loading Fonts with Pillow

```python
from justmytype import get_default_registry
from PIL import Image, ImageDraw, ImageFont

registry = get_default_registry()
font_info = registry.find_font("Arial", weight=700)

if font_info:
    # Load as PIL ImageFont
    font = font_info.load(size=24)

    # Use with PIL
    img = Image.new("RGB", (200, 100), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Hello", font=font, fill="black")
    img.save("output.png")
```

### Blocking Font Packs

```python
# Block system fonts
registry = FontRegistry(blocklist={"system-fonts"})

# Block via environment variable
# FONT_DISCOVERY_BLOCKLIST="system-fonts,broken-pack" python app.py
```

## Command-Line Interface

JustMyType includes a CLI for discovering and inspecting fonts from the command line.

### Find vs Info

- **`find`** — Resolves a single font (best match for family/weight/style/width). Use it when you need a path or a quick answer: one font file, with pack and license when available.
- **`info`** — Rich view of a font family: pack metadata (version, description, licenses) and all variants. Use it when you want to see where the family comes from and what styles exist.

### Family names

Matching is by **exact family name** (case-insensitive). Use the name as it appears in the font, not a shortened or partial form. For example, use `"Noto Sans"` (from `justmytype list`), not `"noto"` or `"notosans"`.

### List All Fonts

```bash
# List families with pack and license (family | pack | license)
justmytype list

# Sort by number of variants
justmytype list --sort count

# Output as JSON (includes family_details with pack and licenses)
justmytype list --json
```

### Find a Font

```bash
# Resolve one font by family name; shows path, pack, license
justmytype find "Roboto"
justmytype find "Noto Sans"

# Find with specific weight and style
justmytype find "Roboto" --weight 400 --style normal
justmytype find "Inter" --weight 700 --style italic

# Output as JSON
justmytype find "Roboto" --json
```

### Show Font Information

```bash
# Rich family view: pack metadata and default variant
justmytype info "Roboto"
justmytype info "Noto Sans"

# Show all variants of the font
justmytype info "Roboto" --all-variants

# Output as JSON
justmytype info "Roboto" --json
```

### List Font Packs

```bash
# List registered font packs (names only)
justmytype packs

# Show description, version, and licenses
justmytype packs --verbose

# Output as JSON (includes manifest when present)
justmytype packs --json
```

### Blocking Font Packs (CLI)

```bash
# Block specific font packs
justmytype list --blocklist "system-fonts"
justmytype find "Roboto" --blocklist "system-fonts,broken-pack"
```

## Creating Font Packs

Creating a font pack involves: (1) **layout** — organizing font files in a directory (or directories) the pack will expose, and optionally adding `pack_manifest.json`; (2) **building** (optional) — using tools such as pack-tools to fetch and assemble families from upstream; (3) **registering** — exposing the pack via the `justmytype.packs` entry point so applications or third-party packages can provide fonts.

### Pack layout and file organization

The entry point factory returns **one or more directory paths** (font directories). The registry scans each font directory for font files (e.g. `.ttf`, `.otf`).

- **Where to put files:** Put font files and optionally `pack_manifest.json` in the directory (or directories) you return. Two common layouts: (a) a Python package that *is* the font directory (e.g. `myapp.fonts` → `myapp/fonts/`); or (b) a package with a `fonts/` subdirectory (e.g. `my_pack/fonts/`). Ensure your package build (e.g. `pyproject.toml` / hatchling) includes those files in the wheel.
- **Optional manifest:** If present, `pack_manifest.json` in a font directory is read by JustMyType for pack metadata (e.g. `justmytype packs --verbose`). Not required for discovery.

### Building packs with pack-tools

For a standard workflow to **build** packs from selected families (e.g. from [Google Fonts](https://github.com/google/fonts)), use **[justmytype-pack-tools](https://github.com/kws/justmytype-essentials/tree/main/pack-tools)** from the [justmytype-essentials](https://github.com/kws/justmytype-essentials) repo. It lets you configure families and upstream in `upstream.toml`, **fetch** families from the upstream repo into a cache, **build** into the pack's font directory (with license resolution and `pack_manifest.json`), and optionally run **manifest** only when fonts are already in place. Usable from the essentials mono-repo or standalone; see the [pack-tools README](https://github.com/kws/justmytype-essentials/blob/main/pack-tools/README.md) for usage and `upstream.toml` schema.

### First-Party Font Pack (Application's Own Fonts)

Register a first-party font pack so your application's bundled fonts are discovered. The factory must return the font directory (or directories) that contain the font files.

```python
# myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory: returns font directory paths for this pack."""
    package = files("myapp.fonts")
    return [Path(str(package))]
```

```toml
# pyproject.toml
[project.entry-points."justmytype.packs"]
"myapp-fonts" = "myapp.fonts:get_font_directories"
```

### Third-Party Font Pack

Register a third-party font pack so the package can provide fonts to any application using JustMyType. The factory must return the font directory (or directories) that contain the font files.

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory: returns font directory paths for this font pack."""
    package = files("my_font_pack.fonts")
    return [Path(str(package))]
```

## Architecture

JustMyType follows a unified "Font Pack" architecture where all font sources (system fonts, bundled fonts, third-party fonts) implement the same `FontPack` protocol. This ensures:

- **Consistency**: All fonts are discovered and resolved the same way
- **Extensibility**: New font sources can be added via EntryPoints
- **Priority**: Font packs (priority 100) override system fonts (priority 0)

See `docs/architecture.md` for detailed architecture documentation.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/justmytype.git
cd justmytype

# Install with development dependencies
pip install -e ".[pillow]"
pip install -e ".[dev]"  # If dev dependencies are configured
```

### Running Tests

```bash
# Run tests with coverage
pytest

# Run with coverage report
pytest --cov=justmytype --cov-report=html
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/
```

## Requirements

- Python 3.10+
- `fonttools` (required)
- `Pillow` (optional, for `FontInfo.load()`)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read the architecture documentation in `docs/architecture.md` and follow the project philosophy outlined in `AGENTS.md`.
