"""JustMyType - Cross-platform font discovery and resolution library."""

from justmytype.core import FontRegistry, get_default_registry
from justmytype.packs.factory import create_system_font_pack
from justmytype.types import FontInfo, FontPack

__version__ = "0.1.0"

__all__ = [
    "FontInfo",
    "FontPack",
    "FontRegistry",
    "create_system_font_pack",
    "get_default_registry",
]

