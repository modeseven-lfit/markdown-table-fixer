# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Tests for table parser."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from markdown_table_fixer.models import MarkdownTable
from markdown_table_fixer.table_parser import (
    MarkdownFileScanner,
    TableParser,
)


@pytest.fixture
def temp_markdown_file(tmp_path: Path) -> Path:
    """Create a temporary markdown file with tables."""
    file_path = tmp_path / "test.md"
    content = dedent("""
        # Test Document

        Some text before the table.

        | Name     | Type   | Description |
        | -------- | ------ | ----------- |
        | foo      | string | A foo value |
        | bar      | int    | A bar value |

        Some text after the table.

        ## Another Section

        | Col1 | Col2 |
        |------|------|
        | A    | B    |
        | C    | D    |
    """).strip()

    file_path.write_text(content)
    return file_path


def test_parser_initialization(temp_markdown_file: Path) -> None:
    """Test parser can be initialized with a file path."""
    parser = TableParser(temp_markdown_file)
    assert parser.file_path == temp_markdown_file


def test_parse_file_finds_tables(temp_markdown_file: Path) -> None:
    """Test that parser can find tables in a file."""
    parser = TableParser(temp_markdown_file)
    tables = parser.parse_file()

    assert len(tables) == 2
    assert all(isinstance(table, MarkdownTable) for table in tables)


def test_parse_file_first_table_structure(temp_markdown_file: Path) -> None:
    """Test that first table is parsed correctly."""
    parser = TableParser(temp_markdown_file)
    tables = parser.parse_file()

    first_table = tables[0]
    assert len(first_table.rows) == 4  # Header + separator + 2 data rows
    assert first_table.column_count == 3
    assert first_table.has_header


def test_parse_file_second_table_structure(temp_markdown_file: Path) -> None:
    """Test that second table is parsed correctly."""
    parser = TableParser(temp_markdown_file)
    tables = parser.parse_file()

    second_table = tables[1]
    assert len(second_table.rows) == 4  # Header + separator + 2 data rows
    assert second_table.column_count == 2
    assert second_table.has_header


def test_separator_row_detection(temp_markdown_file: Path) -> None:
    """Test that separator rows are properly detected."""
    parser = TableParser(temp_markdown_file)
    tables = parser.parse_file()

    # Check first table's separator
    first_table = tables[0]
    assert first_table.rows[1].is_separator
    assert not first_table.rows[0].is_separator
    assert not first_table.rows[2].is_separator


def test_parse_malformed_table(tmp_path: Path) -> None:
    """Test parsing a table with inconsistent columns."""
    file_path = tmp_path / "malformed.md"
    content = dedent("""
        | Col1 | Col2 | Col3 |
        |------|------|
        | A    | B    | C    |
    """).strip()
    file_path.write_text(content)

    parser = TableParser(file_path)
    tables = parser.parse_file()

    # Should still parse the table
    assert len(tables) == 1


def test_parse_empty_file(tmp_path: Path) -> None:
    """Test parsing an empty file."""
    file_path = tmp_path / "empty.md"
    file_path.write_text("")

    parser = TableParser(file_path)
    tables = parser.parse_file()

    assert len(tables) == 0


def test_parse_file_no_tables(tmp_path: Path) -> None:
    """Test parsing a file with no tables."""
    file_path = tmp_path / "no_tables.md"
    content = dedent("""
        # Document

        Just some text.

        - List item 1
        - List item 2

        More text.
    """).strip()
    file_path.write_text(content)

    parser = TableParser(file_path)
    tables = parser.parse_file()

    assert len(tables) == 0


def test_scanner_finds_markdown_files(tmp_path: Path) -> None:
    """Test that scanner finds markdown files."""
    # Create some markdown files
    (tmp_path / "file1.md").write_text("# Test")
    (tmp_path / "file2.markdown").write_text("# Test")
    (tmp_path / "file3.txt").write_text("Not markdown")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file4.md").write_text("# Test")

    scanner = MarkdownFileScanner(tmp_path)
    files = scanner.find_markdown_files()

    # Should find 3 markdown files
    assert len(files) == 3
    assert all(f.suffix.lower() in {".md", ".markdown"} for f in files)


def test_scanner_single_file(tmp_path: Path) -> None:
    """Test scanner with a single file path."""
    file_path = tmp_path / "test.md"
    file_path.write_text("# Test")

    scanner = MarkdownFileScanner(file_path)
    files = scanner.find_markdown_files()

    assert len(files) == 1
    assert files[0] == file_path


def test_scanner_non_markdown_file(tmp_path: Path) -> None:
    """Test scanner with a non-markdown file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Not markdown")

    scanner = MarkdownFileScanner(file_path)
    files = scanner.find_markdown_files()

    assert len(files) == 0


def test_table_line_numbers(temp_markdown_file: Path) -> None:
    """Test that line numbers are correctly tracked."""
    parser = TableParser(temp_markdown_file)
    tables = parser.parse_file()

    first_table = tables[0]
    # Should start around line 5 (after heading and blank line)
    assert first_table.start_line > 0
    assert first_table.end_line > first_table.start_line

    # Each row should have its line number
    for row in first_table.rows:
        assert row.line_number > 0
