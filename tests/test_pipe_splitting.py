# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test pipe splitting functionality."""

from pathlib import Path

import pytest

from markdown_table_fixer.table_parser import TableParser


@pytest.fixture
def parser(tmp_path: Path) -> TableParser:
    """Create a TableParser instance for testing."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")
    return TableParser(test_file)


def test_split_simple_pipes(parser: TableParser) -> None:
    """Test splitting simple text with regular pipes."""
    text = "| Column 1 | Column 2 | Column 3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Column 1 ", " Column 2 ", " Column 3 ", ""]


def test_split_escaped_pipe(parser: TableParser) -> None:
    """Test that escaped pipes are not treated as separators."""
    text = r"| Column 1 | Data with \| pipe | Column 3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == [
        "",
        " Column 1 ",
        r" Data with \| pipe ",
        " Column 3 ",
        "",
    ]


def test_split_html_entity_pipe(parser: TableParser) -> None:
    """Test that HTML entity pipes are not treated as separators."""
    text = "| Column 1 | Data with &#124; pipe | Column 3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == [
        "",
        " Column 1 ",
        " Data with &#124; pipe ",
        " Column 3 ",
        "",
    ]


def test_split_multiple_escaped_pipes(parser: TableParser) -> None:
    """Test handling of multiple escaped pipes in one cell."""
    text = r"| Col1 | \| \| \| | Col3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Col1 ", r" \| \| \| ", " Col3 ", ""]


def test_split_consecutive_escaped_pipes(parser: TableParser) -> None:
    """Test consecutive escaped pipes without spaces."""
    text = r"| Col1 | \|\| | Col3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Col1 ", r" \|\| ", " Col3 ", ""]


def test_split_mixed_escaped_and_html_pipes(parser: TableParser) -> None:
    """Test mixing escaped pipes and HTML entity pipes."""
    text = r"| Col1 | \| and &#124; | Col3 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Col1 ", r" \| and &#124; ", " Col3 ", ""]


def test_split_pipe_at_beginning(parser: TableParser) -> None:
    """Test text starting with a pipe."""
    text = "| First cell"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " First cell"]


def test_split_pipe_at_end(parser: TableParser) -> None:
    """Test text ending with a pipe."""
    text = "Last cell |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["Last cell ", ""]


def test_split_single_pipe(parser: TableParser) -> None:
    """Test a single pipe character."""
    text = "|"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", ""]


def test_split_no_pipes(parser: TableParser) -> None:
    """Test text without any pipes."""
    text = "No pipes here"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["No pipes here"]


def test_split_only_escaped_pipes(parser: TableParser) -> None:
    """Test text with only escaped pipes."""
    text = r"\|\|"
    result = parser._split_by_unescaped_pipes(text)
    assert result == [r"\|\|"]


def test_split_only_html_entity_pipes(parser: TableParser) -> None:
    """Test text with only HTML entity pipes."""
    text = "&#124;&#124;"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["&#124;&#124;"]


def test_split_empty_string(parser: TableParser) -> None:
    """Test empty string."""
    text = ""
    result = parser._split_by_unescaped_pipes(text)
    # Empty string returns empty list
    assert result == []


def test_split_escaped_pipe_at_start(parser: TableParser) -> None:
    """Test escaped pipe at the start of text."""
    text = r"\| starts with pipe"
    result = parser._split_by_unescaped_pipes(text)
    assert result == [r"\| starts with pipe"]


def test_split_escaped_pipe_at_end(parser: TableParser) -> None:
    """Test escaped pipe at the end of text."""
    text = r"ends with pipe \|"
    result = parser._split_by_unescaped_pipes(text)
    assert result == [r"ends with pipe \|"]


def test_split_html_entity_at_start(parser: TableParser) -> None:
    """Test HTML entity pipe at the start of text."""
    text = "&#124; starts with entity"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["&#124; starts with entity"]


def test_split_html_entity_at_end(parser: TableParser) -> None:
    """Test HTML entity pipe at the end of text."""
    text = "ends with entity &#124;"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["ends with entity &#124;"]


def test_split_empty_cells(parser: TableParser) -> None:
    """Test multiple consecutive pipes creating empty cells."""
    text = "|||"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", "", "", ""]


def test_split_mixed_empty_and_content(parser: TableParser) -> None:
    """Test mix of empty cells and cells with content."""
    text = "| Content || Another |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Content ", "", " Another ", ""]


def test_split_whitespace_only_cells(parser: TableParser) -> None:
    """Test cells containing only whitespace."""
    text = "|   |  |     |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", "   ", "  ", "     ", ""]


def test_split_special_characters(parser: TableParser) -> None:
    """Test cells with special characters."""
    text = "| $#@! | *&^% | <>[] |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " $#@! ", " *&^% ", " <>[] ", ""]


def test_split_unicode_characters(parser: TableParser) -> None:
    """Test cells with Unicode characters."""
    text = "| 中文 | émojis 😀 | Ω |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " 中文 ", " émojis 😀 ", " Ω ", ""]


def test_split_code_with_pipes(parser: TableParser) -> None:
    """Test cells containing code with backticks and pipes."""
    text = "| `code` | `cmd | grep` | text |"
    result = parser._split_by_unescaped_pipes(text)
    # The pipe inside backticks is treated as a regular separator
    # This is expected behavior as backtick parsing is not in scope
    assert result == ["", " `code` ", " `cmd ", " grep` ", " text ", ""]


def test_split_partial_html_entity(parser: TableParser) -> None:
    """Test partial HTML entity that shouldn't be matched."""
    text = "| &#12 | &#1234 | normal |"
    result = parser._split_by_unescaped_pipes(text)
    # Partial entities are treated as regular text with separators
    assert result == ["", " &#12 ", " &#1234 ", " normal ", ""]


def test_split_escaped_backslash_before_pipe(parser: TableParser) -> None:
    """Test backslash that's not escaping a pipe."""
    text = r"| text\ | normal |"
    result = parser._split_by_unescaped_pipes(text)
    # The backslash followed by space, then pipe separator
    assert result == ["", r" text\ ", " normal ", ""]


def test_split_real_table_row(parser: TableParser) -> None:
    """Test a realistic table row."""
    text = "| Feature | Status | Notes |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Feature ", " Status ", " Notes ", ""]


def test_split_separator_row(parser: TableParser) -> None:
    """Test a table separator row."""
    text = "|---------|--------|-------|"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", "---------", "--------", "-------", ""]


def test_split_alignment_separator(parser: TableParser) -> None:
    """Test separator row with alignment markers."""
    text = "|:--------|:------:|------:|"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", ":--------", ":------:", "------:", ""]


def test_split_long_content(parser: TableParser) -> None:
    """Test cell with long content."""
    long_text = "This is a very long cell content " * 10
    text = f"| {long_text} | Short |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", f" {long_text} ", " Short ", ""]
    assert len(result[1]) > 100  # Verify the long text is preserved


def test_split_newline_characters(parser: TableParser) -> None:
    """Test that newlines in text are preserved."""
    text = "| Cell1\n | Cell2 |"
    result = parser._split_by_unescaped_pipes(text)
    # Newlines are treated as regular characters
    assert result == ["", " Cell1\n ", " Cell2 ", ""]


def test_split_tab_characters(parser: TableParser) -> None:
    """Test that tab characters are preserved."""
    text = "| Cell1\t | \tCell2 |"
    result = parser._split_by_unescaped_pipes(text)
    assert result == ["", " Cell1\t ", " \tCell2 ", ""]
