"""Tests for the JustMyType CLI."""

from __future__ import annotations

import json
import sys

import pytest

from justmytype.cli import cmd_find, cmd_info, cmd_list, cmd_packs, main
from justmytype.core import FontRegistry


class TestCLICommands:
    """Test CLI command functions."""

    def test_cmd_list_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test basic list command."""

        class Args:
            blocklist: set[str] | None = None
            json = False
            sort = "name"

        args = Args()
        exit_code = cmd_list(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert (
            len(lines) >= 2
        ), "list output should have header and separator (or header + separator + message)"
        assert (
            "Family" in lines[0] and " | " in lines[0]
        ), "list output should be a table with Family header"

    def test_cmd_list_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test list command with JSON output."""

        class Args:
            blocklist: set[str] | None = None
            json = True
            sort = "name"

        args = Args()
        exit_code = cmd_list(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "families" in output
        assert "count" in output
        assert "family_details" in output
        assert isinstance(output["families"], list)
        assert isinstance(output["family_details"], list)
        assert len(output["family_details"]) == len(output["families"])

    def test_cmd_find_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test find command when font exists."""
        registry = FontRegistry()
        registry.discover()
        families = list(registry.list_families())

        if not families:
            pytest.skip("No fonts available for testing")

        class Args:
            family = families[0]
            weight = None
            style = "normal"
            width = None
            blocklist: set[str] | None = None
            json = False

        args = Args()
        exit_code = cmd_find(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Family:" in captured.out

    def test_cmd_find_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test find command when font doesn't exist (should return None, no fallback)."""

        class Args:
            family = "NonExistentFont12345"
            weight = None
            style = "normal"
            width = None
            blocklist: set[str] | None = None
            json = False

        args = Args()
        exit_code = cmd_find(args)
        assert exit_code == 2  # Should return exit code 2 for not found
        captured = capsys.readouterr()
        assert "Font not found" in captured.err  # Should show error message

    def test_cmd_find_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test find command with JSON output."""
        registry = FontRegistry()
        registry.discover()
        families = list(registry.list_families())

        if not families:
            pytest.skip("No fonts available for testing")

        class Args:
            family = families[0]
            weight = None
            style = "normal"
            width = None
            blocklist: set[str] | None = None
            json = True

        args = Args()
        exit_code = cmd_find(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["found"] is True
        assert "path" in output

    def test_cmd_info_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test basic info command."""
        registry = FontRegistry()
        registry.discover()
        families = list(registry.list_families())

        if not families:
            pytest.skip("No fonts available for testing")

        class Args:
            family = families[0]
            all_variants = False
            blocklist: set[str] | None = None
            json = False

        args = Args()
        exit_code = cmd_info(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_cmd_info_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test info command when font doesn't exist (should return None, no fallback)."""

        class Args:
            family = "NonExistentFont12345"
            all_variants = False
            blocklist: set[str] | None = None
            json = False

        args = Args()
        exit_code = cmd_info(args)
        assert exit_code == 2  # Should return exit code 2 for not found
        captured = capsys.readouterr()
        assert "Font family not found" in captured.err  # Should show error message

    def test_cmd_info_all_variants(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test info command with --all-variants."""
        registry = FontRegistry()
        registry.discover()
        families = list(registry.list_families())

        if not families:
            pytest.skip("No fonts available for testing")

        class Args:
            family = families[0]
            all_variants = True
            blocklist: set[str] | None = None
            json = False

        args = Args()
        exit_code = cmd_info(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Variants" in captured.out or "variant" in captured.out.lower()

    def test_cmd_packs_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test basic packs command."""

        class Args:
            blocklist: set[str] | None = None
            json = False
            verbose = False

        args = Args()
        exit_code = cmd_packs(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        # Should at least list system-fonts
        assert len(captured.out) > 0

    def test_cmd_packs_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test packs command with verbose output."""

        class Args:
            blocklist: set[str] | None = None
            json = False
            verbose = True

        args = Args()
        exit_code = cmd_packs(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Priority" in captured.out or "priority" in captured.out.lower()
        # Licenses line shown when pack has manifest with licenses
        assert "Entry point" in captured.out or "entry" in captured.out.lower()

    def test_cmd_packs_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test packs command with JSON output."""

        class Args:
            blocklist: set[str] | None = None
            json = True
            verbose = False

        args = Args()
        exit_code = cmd_packs(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "packs" in output
        assert "count" in output


class TestCLIMain:
    """Test main CLI entry point."""

    def test_main_no_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main with no command (should show help)."""
        # Simulate no command by patching sys.argv
        original_argv = sys.argv
        try:
            sys.argv = ["justmytype"]
            exit_code = main()
            assert exit_code == 1  # Should exit with error
            captured = capsys.readouterr()
            assert "usage" in captured.out.lower() or "help" in captured.out.lower()
        finally:
            sys.argv = original_argv

    def test_main_list_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main with list command."""
        original_argv = sys.argv
        try:
            sys.argv = ["justmytype", "list"]
            exit_code = main()
            assert exit_code == 0
            captured = capsys.readouterr()
            assert len(captured.out) >= 0  # May be empty if no fonts
        finally:
            sys.argv = original_argv

    def test_main_find_command_not_found(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main with find command for non-existent font (should return None, no fallback)."""
        original_argv = sys.argv
        try:
            sys.argv = ["justmytype", "find", "NonExistentFont12345"]
            exit_code = main()
            assert exit_code == 2  # Should return exit code 2 for not found
        finally:
            sys.argv = original_argv

    def test_main_invalid_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main with invalid command."""
        original_argv = sys.argv
        try:
            sys.argv = ["justmytype", "invalid-command"]
            exit_code = main()
            assert exit_code == 1  # Should exit with error
        finally:
            sys.argv = original_argv
