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

## Creating Font Packs

Font packs can be registered via Python EntryPoints. This allows applications to bundle fonts or third-party packages to provide fonts.

### First-Party Font Pack (Application's Own Fonts)

```python
# myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for application's bundled fonts."""
    package = files("myapp.fonts")
    return [Path(str(package))]
```

```toml
# pyproject.toml
[project.entry-points."fontpacks"]
"myapp-fonts" = "myapp.fonts:get_font_directories"
```

### Third-Party Font Pack

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for font pack."""
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
