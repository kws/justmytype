# Font Discovery Architecture

## 1. Overview

This document describes the architecture and design for a standalone font discovery system that combines platform-specific system font detection with extensible font pack discovery via Python EntryPoints.

### 1.1 Purpose

The font discovery system provides a unified interface for locating and resolving fonts from multiple sources, all implemented as Font Packs:

1. **System Font Pack**: Built-in pack exposing platform-specific system font directories (macOS, Linux, Windows)
2. **User Font Packs**: Font packages discovered via Python EntryPoints (supports both first-party application fonts and third-party font packages)

All font sources implement the same `FontPack` protocol, ensuring a unified and extensible architecture.

### 1.2 Core Value Proposition

- **Cross-platform**: Unified API across macOS, Linux, and Windows
- **Extensible**: Font packs can be added via standard Python EntryPoints mechanism
- **Efficient**: Lazy discovery with in-memory caching
- **Flexible**: Supports font matching by family, weight, and style with intelligent fallback

### 1.3 Influences & Similar Systems

- **fontlib** (Python): Demonstrates multi-source font management with EntryPoints
- **system-fonts** (Rust): Reference implementation for locale-aware, platform-specific font discovery
- **font-kit** (Rust): Cross-platform font library interface with system font enumeration
- **Fontsource**: NPM-based self-hosted font packages with version locking

## 2. Architecture Overview

The font discovery system follows a two-tier discovery model:

```
┌─────────────────────────────────────────────────────────┐
│                    Font Registry                        │
│  (Unified interface for font lookup and resolution)     │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐
│ System Fonts │ │ Font Packs   │
│  Discovery   │ │  Discovery   │
└──────────────┘ └──────────────┘
        │               │
        ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Platform-    │ │ EntryPoints  │
│ specific     │ │ mechanism    │
│ paths        │ │              │
└──────────────┘ └──────────────┘
```

### 2.1 Discovery Order

Fonts are discovered in the following priority order:

1. **Font Packs** (Highest Priority): Explicitly registered fonts (first-party or dependencies) via EntryPoints
2. **System Fonts** (Lowest Priority): Fallback to locally installed fonts in platform-specific directories

*Rationale: Ensures application consistency (branding/layout) regardless of the user's local environment. Font Packs represent bundled/application intent - if a developer explicitly adds a font pack, they want that specific version of the font. System fonts serve as the fallback.*

## 3. System Font Pack

The System Font Pack is a built-in Font Pack that exposes the host operating system's fonts. It implements the standard `FontPack` protocol (see Section 4) and is automatically registered with priority 0 (lowest priority).

### 3.1 SystemFontPack Implementation

The System Font Pack is implemented as an abstract base class with OS-specific subclasses to avoid conditional logic and improve maintainability:

```python
from abc import ABC, abstractmethod

class SystemFontPack(ABC):
    """
    Abstract base class for platform-specific system font packs.
    This implements the standard Font Pack protocol.
    """
    
    @abstractmethod
    def get_font_directories(self) -> list[Path]:
        """Returns platform-specific system paths."""
        ...
    
    def get_priority(self) -> int:
        """Returns the priority of this pack (0 = lowest)."""
        return 0
    
    def get_name(self) -> str:
        """Returns the canonical name for this pack (used in blocklist)."""
        return "system-fonts"


class DarwinSystemFontPack(SystemFontPack):
    """System font pack for macOS."""
    
    def get_font_directories(self) -> list[Path]:
        return [
            Path("/System/Library/Fonts"),      # System fonts
            Path("/Library/Fonts"),              # System-wide fonts
            Path.home() / "Library" / "Fonts",  # User fonts
        ]


class WindowsSystemFontPack(SystemFontPack):
    """System font pack for Windows."""
    
    def get_font_directories(self) -> list[Path]:
        return [
            Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
        ]


class LinuxSystemFontPack(SystemFontPack):
    """System font pack for Linux."""
    
    def get_font_directories(self) -> list[Path]:
        return [
            Path.home() / ".fonts",                          # Legacy user fonts
            Path("/usr/share/fonts"),                        # System fonts
            Path("/usr/local/share/fonts"),                 # Local system fonts
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "fonts",  # User fonts (XDG Base Directory)
            Path("/run/host/fonts"),                         # Flatpak/Snap sandbox fonts
        ]


def create_system_font_pack() -> SystemFontPack:
    """Factory function to create the appropriate system font pack for the current platform."""
    system = platform.system()
    if system == "Darwin":
        return DarwinSystemFontPack()
    elif system == "Windows":
        return WindowsSystemFontPack()
    elif system == "Linux":
        return LinuxSystemFontPack()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")
```

### 3.2 Platform-Specific Directories

The OS-specific `SystemFontPack` subclasses return platform-specific directories as follows:

#### macOS

```python
[
    Path("/System/Library/Fonts"),      # System fonts
    Path("/Library/Fonts"),              # System-wide fonts
    Path.home() / "Library" / "Fonts",  # User fonts
]
```

#### Linux

```python
[
    Path.home() / ".fonts",                          # Legacy user fonts
    Path("/usr/share/fonts"),                        # System fonts
    Path("/usr/local/share/fonts"),                 # Local system fonts
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "fonts",  # User fonts (XDG Base Directory)
    Path("/run/host/fonts"),                         # Flatpak/Snap sandbox fonts
]
```

#### Windows

```python
[
    Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
]
```

### 3.3 Font File Discovery

Font files are discovered by recursively scanning directories for common font file extensions:

- `.ttf` - TrueType Font
- `.otf` - OpenType Font
- `.ttc` - TrueType Collection
- `.woff` - Web Open Font Format
- `.woff2` - Web Open Font Format 2.0

**Note**: While `.woff` and `.woff2` are web font formats, they may appear in system directories and should be supported for completeness.

### 3.4 Implementation Considerations

- **Permission Handling**: Gracefully handle directories that cannot be read (OSError, PermissionError)
- **Symlink Resolution**: Follow symlinks to discover fonts in linked directories
- **Performance**: Use lazy discovery - only scan directories when `discover()` is called
- **Caching**: Cache discovered fonts in memory to avoid repeated filesystem scans

## 4. Font Pack Discovery

Font packs are font packages discovered via Python EntryPoints. This mechanism supports both:

- **First-party fonts**: Application's own fonts registered via EntryPoint in the application's `pyproject.toml`
- **Third-party fonts**: Separate font packages installed as dependencies

All font packs, including the built-in System Font Pack, implement the same `FontPack` protocol, providing a unified approach for all font sources.

### 4.1 FontPack Protocol

All font sources, including the internal System Font scanner, must implement the `FontPack` protocol. This protocol requires:

```python
class FontPack(Protocol):
    """Protocol that all font sources must implement."""
    
    def get_font_directories(self) -> list[Path]:
        """Return list of directories containing font files."""
        ...
    
    def get_priority(self) -> int:
        """Return priority for this pack (higher = processed first, overrides lower priority).
        
        Standard priorities:
        - User Font Packs: 100
        - System Font Pack: 0
        """
        ...
    
    def get_name(self) -> str:
        """Return canonical name for this pack (used in blocklist).
        
        Must be unique and stable. System pack uses "system-fonts".
        """
        ...
```

### 4.2 EntryPoints Mechanism

Font packs register themselves using the EntryPoints mechanism defined in PEP 621 and implemented by `importlib.metadata` (Python 3.8+) or `importlib_metadata` (backport).

**Entry Point Group**: `fontpacks` (or project-specific like `myproject.fontpacks`)

**Entry Point Format**: Factory function that returns font directory paths

### 4.3 Font Pack Structure

A font pack (whether first-party or third-party) should define an entry point in its `setup.py` or `pyproject.toml`:

**setup.py**:
```python
setup(
    name="my-font-pack",
    entry_points={
        "fontpacks": [
            "my-font-pack = my_font_pack:get_font_directories",
        ],
    },
)
```

**pyproject.toml**:
```toml
[project.entry-points."fontpacks"]
"my-font-pack" = "my_font_pack:get_font_directories"
```

### 4.4 Font Pack Implementation

The entry point factory function returns font directory paths. This works the same way for both first-party and third-party font packs:

**Example: First-party font pack (application's own fonts)**

```python
# myapp/__init__.py or myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for application's bundled fonts."""
    package = files("myapp.fonts")
    return [Path(str(package))]
```

**Example: Third-party font pack (separate package)**

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory returning font directory paths."""
    # Option 1: Return Path objects
    package = files("my_font_pack.fonts")
    return [Path(str(package))]
    
    # Option 2: Return string paths
    # return [str(Path(__file__).parent / "fonts")]
    
    # Option 3: Return multiple directories
    # return [
    #     Path(str(files("my_font_pack.fonts"))),
    #     Path.home() / ".my_font_pack" / "fonts",
    # ]
```

**Example: Application registering its own fonts in pyproject.toml**

```toml
[project.entry-points."fontpacks"]
"myapp-fonts" = "myapp:get_font_directories"
```

### 4.5 Discovery Implementation

```python
def get_font_pack_directories() -> list[tuple[Path, int, str]]:
    """Get font pack directories from entry points.
    
    Returns list of (directory, priority, name) tuples.
    """
    packs: list[tuple[Path, int, str]] = []
    
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="fontpacks")
    except ImportError:
        # Python < 3.10 fallback
        try:
            import importlib_metadata
            eps = importlib_metadata.entry_points(group="fontpacks")
        except ImportError:
            return packs
    
    for ep in eps:
        try:
            factory = ep.load()
            pack = factory()  # Should return FontPack instance
            
            # Get directories, priority, and name
            dirs = pack.get_font_directories()
            priority = pack.get_priority() if hasattr(pack, 'get_priority') else 100
            name = pack.get_name() if hasattr(pack, 'get_name') else ep.name
            
            for dir_path in dirs:
                path = Path(dir_path) if isinstance(dir_path, str) else dir_path
                if path.exists():
                    packs.append((path, priority, name))
        except Exception:
            # Skip invalid entry points
            continue
    
    return packs
```

## 5. Font Metadata Parsing

Font metadata (family name, weight, style) must be extracted from font files to enable intelligent matching.

### 5.1 Font Parsing Libraries

**Required**: `fonttools`
- Comprehensive font metadata extraction
- Supports TTF, OTF, TTC, WOFF, WOFF2
- Access to OpenType tables (name, OS/2, head)
- **Critical**: Parsing binary font tables is the only reliable way to get family names. Filename heuristics fail ~30% of the time (e.g., "Arial Narrow" is a family, not just "Arial" with a weight).

**Note**: If fonttools is unavailable, the implementation should log a warning and skip the file rather than guessing. Guessing leads to "ghost bugs" where fonts appear with wrong weights or family names.

### 5.2 FontInfo Data Structure

```python
@dataclass(frozen=True, slots=True)
class FontInfo:
    """Information about a discovered font."""
    
    path: Path                    # Path to font file
    family: str                   # Font family name
    weight: int | None = None     # Font weight (100-900, None if unknown)
    style: str = "normal"         # "normal" or "italic"
    width: str | None = None      # Font width/stretch (e.g., "normal", "condensed", "expanded", None if unknown)
    postscript_name: str | None = None  # PostScript name (e.g., "Roboto-BoldItalic") for native OS APIs
    variant: str | None = None    # e.g., "Regular", "Bold", "Italic", "Bold Italic"
```

### 5.3 Metadata Extraction

#### Using fonttools (Required)

```python
from fonttools.ttLib import TTFont

def parse_font_file(path: Path) -> FontInfo | None:
    """Parse font file using fonttools."""
    try:
        font = TTFont(str(path))
        
        # Extract family name from name table
        name_table = font.get("name")
        family = name_table.getDebugName(1)  # Family name
        
        # Extract PostScript name (name ID 6)
        postscript_name = name_table.getDebugName(6)
        
        # Extract weight from OS/2 table
        os2 = font.get("OS/2")
        weight = os2.usWeightClass if os2 else None
        
        # Extract style from name table or OS/2
        style = "normal"
        if os2 and os2.fsSelection & 0x01:  # Italic bit
            style = "italic"
        
        # Extract width/stretch from OS/2 table
        width = None
        if os2:
            # Map OS/2 usWidthClass to CSS width values
            width_map = {
                1: "ultra-condensed", 2: "extra-condensed", 3: "condensed",
                4: "semi-condensed", 5: "normal", 6: "semi-expanded",
                7: "expanded", 8: "extra-expanded", 9: "ultra-expanded"
            }
            width = width_map.get(os2.usWidthClass, "normal")
        
        return FontInfo(
            path=path,
            family=family,
            weight=weight,
            style=style,
            width=width,
            postscript_name=postscript_name,
        )
    except Exception:
        return None
```

### 5.4 Filename-Based Heuristics (Experimental/Unreliable)

**Warning**: Filename-based parsing is unreliable and should only be used as a last resort when fonttools is unavailable. This method fails ~30% of the time and cannot distinguish between font families and width variants (e.g., "Arial Narrow" vs "Arial" with condensed width).

When font metadata is unavailable, parse weight and style from filename:

```python
def parse_filename(path: Path) -> tuple[int | None, str]:
    """Parse weight and style from filename."""
    stem = path.stem.lower()
    weight: int | None = None
    style = "normal"
    
    # Weight mapping
    weight_map = {
        "thin": 100, "extralight": 200, "light": 300,
        "regular": 400, "normal": 400, "medium": 500,
        "semibold": 600, "bold": 700, "extrabold": 800, "black": 900,
    }
    
    for keyword, w in weight_map.items():
        if keyword in stem:
            weight = w
            break
    
    # Style detection
    if "italic" in stem or "oblique" in stem:
        style = "italic"
    
    return weight, style
```

## 6. Font Resolution Algorithm

The resolution mechanism follows the W3C CSS Fonts Level 4 matching algorithm to ensure behavior consistent with browsers and standard design tools.

### 6.1 Matching Hierarchy

When `find_font(family, weight, style, width)` is called, the library filters the font pool in this strict order:

1. **Family Match:**
   - Exact case-insensitive match of the specific family name (e.g., "Open Sans").
   - *If no match:* Check widely known aliases (e.g., "Arial" -> "Liberation Sans" on Linux).
   - *If still no match:* Fall back to the system default font (e.g., San Francisco on macOS, Segoe UI on Windows).

2. **Stretch Match (Width):**
   - Filter available faces to the closest stretch (e.g., if "condensed" is requested, prefer "semi-condensed" over "expanded").
   - Uses the 9-point width scale: ultra-condensed, extra-condensed, condensed, semi-condensed, normal, semi-expanded, expanded, extra-expanded, ultra-expanded.

3. **Style Match:**
   - If `italic` is requested: Prefer `italic` > `oblique` > `normal`.
   - If `normal` is requested: Prefer `normal` > `oblique` > `italic`.

4. **Weight Match:**
   - If the exact weight is missing, follow the standard CSS fallback:
     - **Target < 400:** Look downwards (lighter), then upwards.
     - **Target > 500:** Look upwards (bolder), then downwards.
     - **Target 400 or 500:** Specific rules for snapping to regular/medium.
   - Example: Requesting "Bold" (700) when only "Black" (900) and "Regular" (400) exist will select "Black" (because >500 biases upward).

### 6.2 Distance Calculation (Implementation)

To implement this efficiently without complex filtering chains, we calculate a "Manhattan Distance" for every font in the resolved family. The font with the lowest distance score is selected.

```python
def find_font(
    self,
    family: str,
    weight: int | None = None,
    style: str = "normal",
    width: str | None = None,
) -> FontInfo | None:
    """Find a font by family, weight, style, and width.
    
    Returns FontInfo object containing the font path and metadata.
    Use load_font() or FontInfo.load() to load as PIL ImageFont if needed.
    """
    self.discover()
    
    # Step 1: Family matching with aliases
    family_lower = family.lower()
    candidates = self._fonts.get(family_lower, [])
    
    # Try aliases if no direct match
    if not candidates:
        candidates = self._try_family_aliases(family_lower)
    
    # System default fallback
    if not candidates:
        candidates = self._get_system_default_font()
    
    if not candidates:
        return None
    
    # Step 2-4: Calculate Manhattan Distance for hierarchical matching
    best: FontInfo | None = None
    best_distance = float('inf')
    
    # Width order for distance calculation
    width_order = ["ultra-condensed", "extra-condensed", "condensed",
                   "semi-condensed", "normal", "semi-expanded",
                   "expanded", "extra-expanded", "ultra-expanded"]
    
    for candidate in candidates:
        distance = self._calculate_distance(
            target_weight=weight,
            target_style=style,
            target_width=width,
            candidate=candidate,
            width_order=width_order
        )
        
        if distance < best_distance:
            best_distance = distance
            best = candidate
    
    if best is None:
        best = candidates[0]  # Fallback to first candidate
    
    # Load and return font
    try:
        return ImageFont.truetype(str(best.path), size=size)
    except Exception:
        return None

def _calculate_distance(
    self,
    target_weight: int | None,
    target_style: str,
    target_width: str | None,
    candidate: FontInfo,
    width_order: list[str],
) -> float:
    """Calculate Manhattan Distance with hierarchy: Stretch > Style > Weight."""
    
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
```

*Note: The font with the lowest distance score is selected. This ensures that stretch (width) is always prioritized over style, which is always prioritized over weight, matching W3C CSS behavior.*

### 6.3 Fallback Strategy

The matching hierarchy (Section 6.1) defines the fallback behavior:

1. **Family Fallback**: If no exact family match, try aliases, then system default font
2. **Attribute Fallback**: Within the matched family, the distance calculation automatically handles:
   - Stretch: Closest width variant
   - Style: Prefers italic > oblique > normal (or reverse for normal requests)
   - Weight: CSS-style directional fallback (lighter/bolder based on target)
3. **Final Fallback**: If no font can be resolved, return `None`

### 6.4 Weight Normalization

Font weight values must be normalized to integers (100-900) for distance calculation. The parser converts string weights to integer values using the following mapping:

```python
WEIGHT_MAP = {
    "thin": 100,
    "hairline": 100,
    "extralight": 200,
    "ultralight": 200,
    "light": 300,
    "book": 350,
    "regular": 400,
    "normal": 400,
    "medium": 500,
    "demibold": 600,
    "semibold": 600,
    "demi": 600,
    "bold": 700,
    "extrabold": 800,
    "ultrabold": 800,
    "black": 900,
    "heavy": 900,
    "extrablack": 950,
    "ultrablack": 950,
}
```

This normalization ensures consistent weight matching regardless of how the weight is specified in font metadata or filenames.

## 7. Caching Strategy

Font discovery and resolution results are cached to improve performance.

### 7.1 Discovery Cache

- **Font Registry**: Cache discovered `FontInfo` objects keyed by family name (lowercase)
- **Priority Handling**: When multiple fonts with the same family name exist, fonts from higher-priority packs override fonts from lower-priority packs in the cache
- **Lazy Discovery**: Only discover fonts when `discover()` is called
- **One-time Discovery**: Mark registry as discovered to avoid repeated scans

### 7.2 Resolution Cache

- **Font Instance Cache**: Cache loaded `ImageFont` objects keyed by `(family, size, weight, style, width)`
- **Path Cache**: Cache font file paths for quick lookup
- **Invalidation**: Remove cache entries if font file becomes unavailable

### 7.3 Cache Implementation

```python
class FontRegistry:
    def __init__(self, blocklist: set[str] | None = None) -> None:
        self._fonts: dict[str, list[FontInfo]] = {}  # family -> [FontInfo]
        self._font_pack_priorities: dict[Path, int] = {}  # path -> priority
        self._font_pack_names: dict[Path, str] = {}  # path -> pack name
        self._cache: dict[tuple[str, int, int | None, str, str | None], Path] = {}
        self._discovered = False
        self._blocklist = self._parse_blocklist(blocklist)
    
    def _parse_blocklist(self, blocklist: set[str] | None) -> set[str]:
        """Parse blocklist from constructor and environment variable."""
        result = set(blocklist) if blocklist else set()
        
        # Merge with environment variable
        env_blocklist = os.environ.get("FONT_DISCOVERY_BLOCKLIST", "")
        if env_blocklist:
            result.update(name.strip() for name in env_blocklist.split(",") if name.strip())
        
        return result
    
    def discover(self) -> None:
        """Discover fonts with priority: High-priority packs first, then low-priority packs."""
        if self._discovered:
            return
        
        # Collect all packs with their priorities
        packs: list[tuple[list[Path], int, str]] = []
        
        # 1. Load System Font Pack (unless blocked)
        if "system-fonts" not in self._blocklist:
            system_pack = create_system_font_pack()
            system_dirs = system_pack.get_font_directories()
            packs.append((system_dirs, system_pack.get_priority(), system_pack.get_name()))
        
        # 2. Load External Packs via EntryPoints
        for ep in self._get_entry_points():
            pack_name = ep.name
            if pack_name in self._blocklist:
                continue  # Skip blocked packs
            
            try:
                factory = ep.load()
                pack = factory()
                dirs = pack.get_font_directories()
                priority = pack.get_priority() if hasattr(pack, 'get_priority') else 100
                packs.append((dirs, priority, pack.get_name() if hasattr(pack, 'get_name') else pack_name))
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
        """Scan directory and add fonts, respecting priority."""
        for font_file in self._find_font_files(dir_path):
            font_info = parse_font_file(font_file)
            if font_info:
                family_lower = font_info.family.lower()
                
                # Check if we should override existing font from lower-priority pack
                should_add = True
                if family_lower in self._fonts:
                    # Check if existing fonts are from lower-priority packs
                    for existing_font in self._fonts[family_lower]:
                        existing_priority = self._font_pack_priorities.get(existing_font.path, -1)
                        if priority <= existing_priority:
                            # This pack has same or lower priority, don't override
                            should_add = False
                            break
                    # If this pack has higher priority, remove lower-priority fonts
                    if should_add:
                        self._fonts[family_lower] = [
                            f for f in self._fonts[family_lower]
                            if self._font_pack_priorities.get(f.path, -1) >= priority
                        ]
                
                if should_add:
                    if family_lower not in self._fonts:
                        self._fonts[family_lower] = []
                    self._fonts[family_lower].append(font_info)
                    self._font_pack_priorities[font_info.path] = priority
                    self._font_pack_names[font_info.path] = pack_name
```

## 8. API Design

### 8.1 Core Classes

#### FontRegistry

```python
class FontRegistry:
    """Registry for discovering and resolving fonts."""
    
    def discover(self) -> None:
        """Discover fonts from all registered packs (high-priority first)."""
        ...
    
    def find_font(
        self,
        family: str,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> FontInfo | None:
        """Find a font by family, weight, style, and width.
        
        Returns FontInfo object containing the font path and metadata.
        Use load_font() or FontInfo.load() to load as PIL ImageFont if needed.
        """
        ...
    
    def load_font(
        self,
        font_info: FontInfo,
        size: int,
    ) -> ImageFont.FreeTypeFont | None:
        """Load a FontInfo object as a PIL ImageFont.
        
        This method imports PIL only when called, keeping JustMyType
        decoupled from Pillow for users who don't need it.
        """
        ...
    
    def list_families(self) -> Iterator[str]:
        """List all discovered font families."""
        ...
    
    def get_font_path(
        self,
        family: str,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> Path | None:
        """Get path to font file."""
        ...
```

#### FontInfo

```python
@dataclass(frozen=True, slots=True)
class FontInfo:
    """Information about a discovered font."""
    path: Path
    family: str
    weight: int | None = None
    style: str = "normal"
    width: str | None = None
    postscript_name: str | None = None
    variant: str | None = None
    
    def load(self, size: int) -> ImageFont.FreeTypeFont | None:
        """Load this font as a PIL ImageFont.
        
        This method imports PIL only when called, keeping JustMyType
        decoupled from Pillow for users who don't need it.
        """
        try:
            from PIL import ImageFont
            return ImageFont.truetype(str(self.path), size=size)
        except ImportError:
            raise ImportError("Pillow (PIL) is required to load fonts. Install with: pip install Pillow")
        except Exception:
            return None
```

### 8.2 Factory Functions

```python
def get_default_registry() -> FontRegistry:
    """Get the default global font registry instance."""
    ...

def get_system_font_directories() -> list[Path]:
    """Get platform-specific system font directories."""
    ...

def get_font_pack_directories() -> list[Path]:
    """Get font pack directories from entry points."""
    ...
```

### 8.3 Font Reference (Optional)

For applications that need to serialize font references:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class FontRef:
    """Font reference that resolves via font registry."""
    
    family: str
    size: int
    weight: int | None = None
    style: str = "normal"
    
    def to_font_info(
        self, registry: FontRegistry | None = None
    ) -> FontInfo | None:
        """Resolve this font reference to a FontInfo object."""
        ...
    
    def to_image_font(
        self, registry: FontRegistry | None = None
    ) -> ImageFont.FreeTypeFont | None:
        """Resolve this font reference to a PIL ImageFont.
        
        Deprecated: Use to_font_info() and FontInfo.load() instead.
        """
        ...
```

### 8.4 Configuration

The font registry supports configuration via constructor arguments and environment variables to enable operational control in various deployment scenarios.

#### Blocklist Support

The blocklist mechanism allows excluding specific font packs from discovery without uninstalling packages. This is essential for:

- **Conflict Resolution**: Ignore conflicting or broken font packs in shared environments
- **Performance**: Disable large font packs (e.g., Google Fonts) for fast-startup CLI tools
- **Debugging**: Isolate font sources to identify which pack provides a specific font
- **Sandboxing**: Block system fonts entirely for pixel-perfect consistency across machines

#### Blocklist Mechanisms

**A. Constructor Argument (Code Control)**

```python
registry = FontRegistry(
    blocklist={"system-fonts", "broken-legacy-pack"}
)
```

**B. Environment Variable (User/Ops Control)**

```bash
# Useful for CI/CD or fixing broken user environments
export FONT_DISCOVERY_BLOCKLIST="system-fonts,broken-pack"
```

The environment variable is parsed as a comma-separated list and merged with any constructor-provided blocklist.

#### Standard Pack Names

The following pack names are reserved/standardized:

- `"system-fonts"`: The built-in System Font Pack (can be blocked to disable system font discovery)

User-defined font packs use their EntryPoint name as the pack identifier. Pack names are case-sensitive.

#### Example Usage

```python
# Disable system fonts for sandboxed environment
registry = FontRegistry(blocklist={"system-fonts"})

# Disable specific third-party pack
registry = FontRegistry(blocklist={"google-fonts"})

# Combine with environment variable
# FONT_DISCOVERY_BLOCKLIST="system-fonts" python app.py
registry = FontRegistry(blocklist={"broken-pack"})  # Both are blocked
```

## 9. Best Practices

### 9.1 Lessons from Existing Solutions

**fontlib**:
- Uses EntryPoints for extensibility
- Supports both API and CLI interfaces
- Demonstrates multi-source font management

**system-fonts** (Rust):
- Locale-aware font selection
- Cached font database for performance
- Best-effort resolution (graceful fallback)

**font-kit**:
- Cross-platform system font enumeration
- Proper font metadata extraction
- Support for variable fonts

### 9.2 Implementation Recommendations

1. **Lazy Discovery**: Only discover fonts when needed
2. **Error Handling**: Gracefully handle missing fonts, permission errors, and invalid font files
3. **Caching**: Cache both discovery results and loaded font instances
4. **Extensibility**: Use EntryPoints for font pack discovery
5. **Platform Abstraction**: Hide platform-specific details behind unified API
6. **Metadata Priority**: Prefer font file metadata over filename heuristics

### 9.3 Performance Considerations

- **One-time Discovery**: Scan filesystem only once per registry instance
- **Lazy Loading**: Load font files only when `find_font()` is called
- **Cache Management**: Use appropriate cache sizes and invalidation strategies
- **Parallel Discovery**: Consider parallel directory scanning for large font collections

## 10. Future Considerations

### 10.1 Locale-Aware Selection

Support locale-based font selection for internationalization:

```python
def find_font_for_locale(
    self,
    family: str,
    locale: str,
    weight: int | None = None,
    style: str = "normal",
) -> FontInfo | None:
    """Find font with locale-aware fallback."""
    # Try exact locale match first
    # Fall back to language family
    # Fall back to default
    ...
```

### 10.2 Font Fallback Chains

Implement CSS-like font fallback chains:

```python
def find_font_with_fallback(
    self,
    families: list[str],  # ["Arial", "Helvetica", "sans-serif"]
    weight: int | None = None,
    style: str = "normal",
) -> FontInfo | None:
    """Find font using fallback chain."""
    for family in families:
        font_info = self.find_font(family, weight, style)
        if font_info:
            return font_info
    return None
```

### 10.3 Variable Fonts

Support variable fonts (OpenType Variable Fonts) with custom axis values:

```python
def find_variable_font(
    self,
    family: str,
    weight: int | None = None,
    width: int | None = None,  # Variable axis
    style: str = "normal",
) -> FontInfo | None:
    """Find variable font (returns FontInfo, variable axis configuration handled separately)."""
    ...
```

### 10.4 Font Validation

Add font validation and integrity checks:

```python
def validate_font(self, path: Path) -> bool:
    """Validate font file integrity."""
    # Check file format
    # Verify font tables
    # Check for corruption
    ...
```

## 11. Design Origins

This design was informed by practical implementations that demonstrated the viability of combining system font discovery with extensible font pack discovery via EntryPoints. The architecture emphasizes:

- **Independence**: Standalone library with minimal framework dependencies
- **Extensibility**: EntryPoints mechanism for third-party font packs
- **Cross-platform**: Unified API across macOS, Linux, and Windows
- **Required Dependencies**: fonttools (required for reliable font metadata extraction)
- **Optional Dependencies**: PIL/Pillow (required only for FontInfo.load() and load_font() methods)

## 12. Example Usage

### 12.1 Basic Usage

```python
from justmytype import FontRegistry, get_default_registry

# Get default registry
registry = get_default_registry()

# Discover fonts (lazy, called automatically on first use)
registry.discover()

# Find a font
font = registry.find_font("Arial", size=16, weight=700, style="normal", width="normal")
if font:
    # Use font with PIL
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (100, 50), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Hello", font=font, fill="black")
```

### 12.2 Custom Registry

```python
from justmytype import FontRegistry

# Create custom registry
registry = FontRegistry()

# Add custom font directory
from pathlib import Path
custom_fonts = Path.home() / "custom_fonts"
# (Would need API extension to add directories)

# Use registry
font_info = registry.find_font("CustomFont")
if font_info:
    font = font_info.load(size=12)
```

### 12.3 Font Pack Implementation

**First-party font pack (application's own fonts):**

```python
# myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for application's bundled fonts."""
    package = files("myapp.fonts")
    return [Path(str(package))]

# pyproject.toml
# [project.entry-points."fontpacks"]
# "myapp-fonts" = "myapp.fonts:get_font_directories"
```

**Third-party font pack (separate package):**

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for font pack."""
    package = files("my_font_pack.fonts")
    return [Path(str(package))]

# pyproject.toml
# [project.entry-points."fontpacks"]
# "my-font-pack" = "my_font_pack:get_font_directories"
```

## 13. Comparison with Existing Solutions

| Feature | This Design | fontlib | system-fonts | font-kit |
|---------|-------------|---------|--------------|----------|
| System Fonts | ✅ | ✅ | ✅ | ✅ |
| Font Packs (EntryPoints) | ✅ | ✅ | ❌ | ❌ |
| Cross-platform | ✅ | ✅ | ✅ | ✅ |
| Locale-aware | 🔄 Future | ❌ | ✅ | ❌ |
| Variable Fonts | 🔄 Future | ❌ | ❌ | ✅ |
| Language | Python | Python | Rust | Rust |

**Key Differentiators**:
- Combines system fonts and pack-based discovery (unified EntryPoints for both first-party and third-party fonts)
- Python-native with EntryPoints extensibility
- Required dependencies: fonttools (font metadata), PIL/Pillow (font loading)
- Font Packs override System Fonts for application consistency
- Designed for standalone project extraction

