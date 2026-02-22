"""JustMyType - Cross-platform font discovery and resolution library."""

from importlib.metadata import PackageNotFoundError, version

from justmytype.core import FontRegistry, get_default_registry
from justmytype.font_catalog import create_catalog
from justmytype.packs.factory import create_system_font_pack
from justmytype.types import FontInfo, FontPack

try:
    __version__ = version("justmytype")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "FontInfo",
    "FontPack",
    "FontRegistry",
    "create_catalog",
    "create_system_font_pack",
    "get_default_registry",
]
