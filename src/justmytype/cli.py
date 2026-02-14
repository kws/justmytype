"""Command-line interface for JustMyType."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from justmytype.core import FontRegistry

if TYPE_CHECKING:
    from justmytype.types import FontInfo


def _get_registry(blocklist: set[str] | None = None) -> FontRegistry:
    """Create a font registry instance.

    Args:
        blocklist: Optional set of font pack names to block.

    Returns:
        FontRegistry instance.
    """
    return FontRegistry(blocklist=blocklist)


def cmd_list(args: argparse.Namespace) -> int:
    """List all available font families.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    registry = _get_registry(blocklist=args.blocklist)
    registry.discover()

    families = list(registry.list_families())

    if args.sort == "count":
        # Sort by number of variants (count of fonts per family)
        # We need to count variants by finding all fonts for each family
        family_counts: dict[str, int] = {}
        for family in families:
            # Count variants by trying to find fonts with different weights/styles
            # This is approximate but works without accessing private attributes
            count = 0
            for weight in [None, 400, 700]:
                for style in ["normal", "italic"]:
                    font_info = registry.find_font(family, weight=weight, style=style)
                    if font_info:
                        count += 1
                        break  # Found at least one variant
            family_counts[family] = count if count > 0 else 1
        families = sorted(families, key=lambda f: family_counts.get(f, 0), reverse=True)
    else:
        # Sort alphabetically
        families = sorted(families)

    if args.json:
        output = {"families": families, "count": len(families)}
        print(json.dumps(output, indent=2))
    else:
        for family in families:
            print(family)

    return 0


def cmd_find(args: argparse.Namespace) -> int:
    """Find a specific font.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 if found, 2 if not found, 1 on error).
    """
    registry = _get_registry(blocklist=args.blocklist)
    registry.discover()

    font_info = registry.find_font(
        family=args.family,
        weight=args.weight,
        style=args.style,
        width=args.width,
    )

    if not font_info:
        if args.json:
            print(json.dumps({"found": False, "family": args.family}, indent=2))
        else:
            print(f"Font not found: {args.family}", file=sys.stderr)
        return 2

    if args.json:
        output = {
            "found": True,
            "family": font_info.family,
            "path": str(font_info.path),
            "weight": font_info.weight,
            "style": font_info.style,
            "width": font_info.width,
            "postscript_name": font_info.postscript_name,
            "variant": font_info.variant,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Found: {font_info.path}")
        print(f"Family: {font_info.family}")
        if font_info.weight is not None:
            print(f"Weight: {font_info.weight}")
        if font_info.style:
            print(f"Style: {font_info.style}")
        if font_info.width:
            print(f"Width: {font_info.width}")
        if font_info.postscript_name:
            print(f"PostScript: {font_info.postscript_name}")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed information about a font family.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 2 if not found).
    """
    registry = _get_registry(blocklist=args.blocklist)
    registry.discover()

    # Try to find the font first to get the actual family name
    font_info = registry.find_font(args.family)
    if not font_info:
        if args.json:
            print(json.dumps({"found": False, "family": args.family}, indent=2))
        else:
            print(f"Font family not found: {args.family}", file=sys.stderr)
        return 2

    # Collect all variants by trying different weights/styles
    # This is a workaround since we don't have direct access to all variants
    fonts: list[FontInfo] = []
    seen_paths: set[Path] = set()

    # Try common weight/style combinations
    for weight in [None, 100, 200, 300, 400, 500, 600, 700, 800, 900]:
        for style in ["normal", "italic"]:
            variant = registry.find_font(args.family, weight=weight, style=style)
            if variant and variant.path not in seen_paths:
                fonts.append(variant)
                seen_paths.add(variant.path)

    if not fonts:
        # Fallback to the one we found
        fonts = [font_info]
    if not fonts:
        if args.json:
            print(json.dumps({"found": False, "family": args.family}, indent=2))
        else:
            print(f"Font family not found: {args.family}", file=sys.stderr)
        return 2

    if args.json:
        variants = []
        for font in fonts:
            variants.append(
                {
                    "family": font.family,
                    "path": str(font.path),
                    "weight": font.weight,
                    "style": font.style,
                    "width": font.width,
                    "postscript_name": font.postscript_name,
                    "variant": font.variant,
                }
            )
        output = {
            "family": fonts[0].family,
            "variants": variants if args.all_variants else [variants[0]],
            "count": len(variants),
        }
        print(json.dumps(output, indent=2))
    else:
        print(fonts[0].family)
        if args.all_variants:
            print(f"  Variants ({len(fonts)}):")
            for font in fonts:
                variant_info = []
                if font.weight is not None:
                    variant_info.append(f"Weight: {font.weight}")
                if font.style:
                    variant_info.append(f"Style: {font.style}")
                if font.width:
                    variant_info.append(f"Width: {font.width}")
                variant_str = ", ".join(variant_info) if variant_info else "default"
                print(f"    - {variant_str}")
                print(f"      Path: {font.path}")
                if font.postscript_name:
                    print(f"      PostScript: {font.postscript_name}")
        else:
            # Show first variant with details
            font = fonts[0]
            print(f"  Path: {font.path}")
            if font.weight is not None:
                print(f"  Weight: {font.weight}")
            if font.style:
                print(f"  Style: {font.style}")
            if font.width:
                print(f"  Width: {font.width}")
            if font.postscript_name:
                print(f"  PostScript: {font.postscript_name}")
            if len(fonts) > 1:
                print(f"  (Total variants: {len(fonts)})")

    return 0


def cmd_packs(args: argparse.Namespace) -> int:
    """List registered font packs.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    registry = _get_registry(blocklist=args.blocklist)
    registry.discover()

    # Get font packs from entry points
    packs: list[dict[str, str | int | list[str]]] = []
    try:
        from importlib.metadata import entry_points
    except ImportError:
        try:
            import importlib_metadata

            entry_points = importlib_metadata.entry_points
        except ImportError:
            entry_points = lambda group: []  # noqa: E731

    eps = entry_points(group="justmytype.packs")
    for ep in eps:
        try:
            factory = ep.load()
            pack = factory()
            if hasattr(pack, "get_name") and hasattr(pack, "get_priority"):
                packs.append(
                    {
                        "name": pack.get_name(),
                        "priority": pack.get_priority(),
                        "entry_point": ep.name,
                    }
                )
        except Exception:
            continue

    # Add system font pack if not blocked
    if "system-fonts" not in (args.blocklist or set()):
        try:
            from justmytype.packs.factory import create_system_font_pack

            system_pack = create_system_font_pack()
            packs.append(
                {
                    "name": system_pack.get_name(),
                    "priority": system_pack.get_priority(),
                    "entry_point": "system-fonts",
                }
            )
        except NotImplementedError:
            pass

    # Sort by priority (highest first)
    packs.sort(key=lambda p: p["priority"], reverse=True)

    if args.json:
        print(json.dumps({"packs": packs, "count": len(packs)}, indent=2))
    else:
        if args.verbose:
            print(f"Registered font packs ({len(packs)}):")
            for pack in packs:
                print(f"  {pack['name']}")
                print(f"    Priority: {pack['priority']}")
                print(f"    Entry point: {pack['entry_point']}")
        else:
            for pack in packs:
                print(pack["name"])

    return 0


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        prog="justmytype",
        description="JustMyType - Cross-platform font discovery and resolution",
    )
    parser.add_argument(
        "--blocklist",
        type=str,
        help="Comma-separated list of font pack names to block",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all available font families")
    list_parser.add_argument(
        "--sort",
        choices=["name", "count"],
        default="name",
        help="Sort order (default: name)",
    )

    # find command
    find_parser = subparsers.add_parser("find", help="Find a specific font")
    find_parser.add_argument("family", help="Font family name")
    find_parser.add_argument(
        "--weight",
        type=int,
        help="Font weight (100-900)",
    )
    find_parser.add_argument(
        "--style",
        choices=["normal", "italic"],
        default="normal",
        help="Font style (default: normal)",
    )
    find_parser.add_argument(
        "--width",
        help="Font width (e.g., normal, condensed, expanded)",
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Show detailed font information")
    info_parser.add_argument("family", help="Font family name")
    info_parser.add_argument(
        "--all-variants",
        action="store_true",
        help="Show all variants of the font",
    )

    # packs command
    packs_parser = subparsers.add_parser("packs", help="List registered font packs")
    packs_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed pack information",
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse raises SystemExit(2) for invalid commands/arguments
        # Return 1 for invalid commands to match expected behavior
        return 1

    # Parse blocklist
    blocklist: set[str] | None = None
    if args.blocklist:
        blocklist = {name.strip() for name in args.blocklist.split(",") if name.strip()}

    # Override args.blocklist with parsed set
    args.blocklist = blocklist

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "list":
            return cmd_list(args)
        elif args.command == "find":
            return cmd_find(args)
        elif args.command == "info":
            return cmd_info(args)
        elif args.command == "packs":
            return cmd_packs(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
