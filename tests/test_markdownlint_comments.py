# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test markdownlint comment parsing."""

from pathlib import Path

import pytest

from markdown_table_fixer.table_fixer import FileFixer


@pytest.fixture
def file_fixer(tmp_path: Path) -> FileFixer:
    """Create a FileFixer instance for testing."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")
    return FileFixer(test_file)


def test_parse_markdownlint_disable_single_rule(file_fixer: FileFixer) -> None:
    """Test parsing a disable comment with a single rule."""
    line = "<!-- markdownlint-disable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}


def test_parse_markdownlint_disable_multiple_rules(
    file_fixer: FileFixer,
) -> None:
    """Test parsing a disable comment with multiple rules."""
    line = "<!-- markdownlint-disable MD013 MD060 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013", "MD060"}


def test_parse_markdownlint_enable_single_rule(file_fixer: FileFixer) -> None:
    """Test parsing an enable comment with a single rule."""
    line = "<!-- markdownlint-enable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "enable")
    assert rules == {"MD013"}


def test_parse_markdownlint_enable_multiple_rules(
    file_fixer: FileFixer,
) -> None:
    """Test parsing an enable comment with multiple rules."""
    line = "<!-- markdownlint-enable MD013 MD060 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "enable")
    assert rules == {"MD013", "MD060"}


def test_parse_markdownlint_with_extra_whitespace(
    file_fixer: FileFixer,
) -> None:
    """Test parsing with extra whitespace."""
    line = "<!--   markdownlint-disable   MD013   MD060   -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013", "MD060"}


def test_parse_markdownlint_no_match(file_fixer: FileFixer) -> None:
    """Test parsing a line without markdownlint comment."""
    line = "This is just a regular line"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == set()


def test_parse_markdownlint_wrong_type(file_fixer: FileFixer) -> None:
    """Test parsing with wrong comment type."""
    line = "<!-- markdownlint-disable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "enable")
    assert rules == set()


def test_parse_markdownlint_false_positive_substring(
    file_fixer: FileFixer,
) -> None:
    """Test that substrings don't cause false matches."""
    # Should NOT match MD013 in "MD013013"
    line = "<!-- This is my MD013013 test -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == set()


def test_parse_markdownlint_false_positive_partial_rule(
    file_fixer: FileFixer,
) -> None:
    """Test that incomplete rule patterns don't match."""
    # Should NOT match incomplete patterns (no digits after MD)
    line = "<!-- markdownlint-disable MD -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == set()

    # Should match valid patterns like MD01 (2 digits) and MD001 (3 digits)
    line = "<!-- markdownlint-disable MD01 MD001 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD01", "MD001"}


def test_parse_markdownlint_mixed_content(file_fixer: FileFixer) -> None:
    """Test parsing with other content in the comment."""
    line = "<!-- markdownlint-disable MD013 MD060 - table too wide -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013", "MD060"}


def test_parse_markdownlint_with_text_before(file_fixer: FileFixer) -> None:
    """Test parsing when there's text before the comment."""
    line = "Some text <!-- markdownlint-disable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}


def test_parse_markdownlint_with_text_after(file_fixer: FileFixer) -> None:
    """Test parsing when there's text after the comment."""
    line = "<!-- markdownlint-disable MD013 --> more text"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}


def test_parse_markdownlint_various_rule_numbers(file_fixer: FileFixer) -> None:
    """Test parsing various valid rule numbers."""
    line = "<!-- markdownlint-disable MD001 MD013 MD060 MD999 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD001", "MD013", "MD060", "MD999"}


def test_parse_markdownlint_no_rules_specified(file_fixer: FileFixer) -> None:
    """Test parsing when no rules are specified."""
    line = "<!-- markdownlint-disable -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == set()


def test_parse_markdownlint_case_sensitive(file_fixer: FileFixer) -> None:
    """Test that rule names are case-sensitive."""
    # Should match uppercase MD
    line = "<!-- markdownlint-disable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}

    # Should NOT match lowercase md
    line_lower = "<!-- markdownlint-disable md013 -->"
    rules_lower = file_fixer._parse_markdownlint_comment(line_lower, "disable")
    assert rules_lower == set()


def test_parse_markdownlint_not_a_comment(file_fixer: FileFixer) -> None:
    """Test that non-comment text is not matched."""
    line = (
        "This line mentions markdownlint-disable MD013 but it's not a comment"
    )
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == set()


def test_parse_markdownlint_multiple_comments_in_line(
    file_fixer: FileFixer,
) -> None:
    """Test that only the first comment is parsed."""
    line = (
        "<!-- markdownlint-disable MD013 --> "
        "<!-- markdownlint-disable MD060 -->"
    )
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    # Should only match the first comment
    assert rules == {"MD013"}


def test_parse_markdownlint_with_newlines(file_fixer: FileFixer) -> None:
    """Test parsing when line has newline characters."""
    line = "<!-- markdownlint-disable MD013 -->\n"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}


def test_parse_markdownlint_different_rule_numbers(
    file_fixer: FileFixer,
) -> None:
    """Test that different rule numbers are properly distinguished."""
    # Should match MD013 but not MD01, MD0013, or other variations
    line = "<!-- markdownlint-disable MD013 -->"
    rules = file_fixer._parse_markdownlint_comment(line, "disable")
    assert rules == {"MD013"}
    assert "MD01" not in rules
    assert "MD0013" not in rules
    assert "MD13" not in rules
