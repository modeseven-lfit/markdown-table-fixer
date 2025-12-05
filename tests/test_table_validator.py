# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test table validator functionality, especially escape logic."""

from pathlib import Path

import pytest

from markdown_table_fixer.models import (
    MarkdownTable,
    TableCell,
    TableRow,
)
from markdown_table_fixer.table_validator import TableValidator


@pytest.fixture
def basic_table(tmp_path: Path) -> MarkdownTable:
    """Create a basic table for testing."""
    return MarkdownTable(
        rows=[],
        start_line=1,
        end_line=3,
        file_path=tmp_path / "test.md",
    )


def create_row_with_raw_line(raw_line: str, line_number: int = 1) -> TableRow:
    """Helper to create a TableRow with a raw line for testing.

    Args:
        raw_line: The raw line text containing pipes
        line_number: Line number in the file

    Returns:
        TableRow with the raw line set
    """
    # Create minimal cells (actual parsing not needed for these tests)
    cells = [TableCell(content="", start_col=0, end_col=0)]
    return TableRow(
        cells=cells,
        line_number=line_number,
        raw_line=raw_line,
        is_separator=False,
    )


def test_simple_pipes(basic_table: MarkdownTable) -> None:
    """Test detection of simple unescaped pipes."""
    row = create_row_with_raw_line("| Col1 | Col2 | Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Should find pipes at positions 0, 7, 14, 21
    assert positions == [0, 7, 14, 21]


def test_single_escaped_pipe(basic_table: MarkdownTable) -> None:
    """Test that a pipe preceded by single backslash is escaped (not detected)."""
    row = create_row_with_raw_line(r"| Col1 | Data \| here | Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Pipe at position 14 is escaped, should not be detected
    # Should find pipes at positions 0, 7, 22, 29
    assert positions == [0, 7, 22, 29]


def test_double_backslash_unescaped_pipe(basic_table: MarkdownTable) -> None:
    """Test \\| (escaped backslash + unescaped pipe - should detect pipe)."""
    row = create_row_with_raw_line(r"| Col1 | Data \\| Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Two backslashes (even count) means pipe is NOT escaped
    # Should find pipes at positions 0, 7, 16, 23
    assert positions == [0, 7, 16, 23]


def test_triple_backslash_escaped_pipe(basic_table: MarkdownTable) -> None:
    """Test \\\\\\| (escaped backslash + escaped pipe - should NOT detect pipe)."""
    row = create_row_with_raw_line(r"| Col1 | Data \\\| Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Three backslashes (odd count) means pipe IS escaped
    # Should find pipes at positions 0, 7, 24
    assert positions == [0, 7, 24]


def test_quadruple_backslash_unescaped_pipe(basic_table: MarkdownTable) -> None:
    """Test \\\\\\\\| (two escaped backslashes + unescaped pipe - should detect)."""
    row = create_row_with_raw_line(r"| Col1 | Data \\\\| Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Four backslashes (even count) means pipe is NOT escaped
    # Should find pipes at positions 0, 7, 18, 25
    assert positions == [0, 7, 18, 25]


def test_multiple_escaped_pipes(basic_table: MarkdownTable) -> None:
    """Test multiple escaped pipes in one row."""
    row = create_row_with_raw_line(r"| Col1 | \| \| \| | Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # All three middle pipes are escaped
    # Should find pipes at positions 0, 7, 18, 25
    assert positions == [0, 7, 18, 25]


def test_mixed_escaped_and_unescaped_pipes(basic_table: MarkdownTable) -> None:
    """Test row with both escaped and unescaped pipes."""
    row = create_row_with_raw_line(r"| Col1 | A \| B | C | D |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Pipe after 'B' is escaped, others are not
    # Should find pipes at positions 0, 7, 16, 20, 24
    assert positions == [0, 7, 16, 20, 24]


def test_pipe_at_start_of_line(basic_table: MarkdownTable) -> None:
    """Test pipe at the very start of the line (no preceding backslashes)."""
    row = create_row_with_raw_line("| Col1 | Col2 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Should find pipes at positions 0, 7, 14
    assert positions == [0, 7, 14]


def test_escaped_pipe_at_position_one(basic_table: MarkdownTable) -> None:
    """Test escaped pipe immediately after first character."""
    row = create_row_with_raw_line(r"|\| Col2 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # First pipe at 0 is unescaped, second at 1 is escaped, third at 9 is unescaped
    assert positions == [0, 9]


def test_no_pipes(basic_table: MarkdownTable) -> None:
    """Test line with no pipes."""
    row = create_row_with_raw_line("No pipes here")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    assert positions == []


def test_only_escaped_pipes(basic_table: MarkdownTable) -> None:
    """Test line where all pipes are escaped."""
    row = create_row_with_raw_line(r"\| \| \|")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # All pipes are escaped, should find none
    assert positions == []


def test_consecutive_pipes(basic_table: MarkdownTable) -> None:
    """Test consecutive unescaped pipes."""
    row = create_row_with_raw_line("| Col1 || Col2 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Should find pipes at positions 0, 7, 8, 15
    assert positions == [0, 7, 8, 15]


def test_backslash_before_non_pipe(basic_table: MarkdownTable) -> None:
    """Test that backslashes before non-pipe characters don't affect pipe detection."""
    row = create_row_with_raw_line(r"| Col1 | Data \n here | Col3 |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Backslash before 'n' doesn't affect pipes
    # Should find pipes at positions 0, 7, 22, 29
    assert positions == [0, 7, 22, 29]


def test_complex_escape_pattern(basic_table: MarkdownTable) -> None:
    """Test complex pattern with various escape scenarios."""
    row = create_row_with_raw_line(r"| A | B \| C | D \\| E | F \\\| G |")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    # Breaking down:
    # Position 0: | - unescaped
    # Position 4: | - unescaped
    # Position 9: \| - escaped (1 backslash, odd)
    # Position 13: | - unescaped
    # Position 19: \\| - unescaped (2 backslashes, even)
    # Position 23: | - unescaped
    # Position 29: \\\| - escaped (3 backslashes, odd)
    # Position 34: | - unescaped
    assert positions == [0, 4, 13, 19, 23, 34]


def test_empty_line(basic_table: MarkdownTable) -> None:
    """Test empty line."""
    row = create_row_with_raw_line("")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    assert positions == []


def test_only_pipe(basic_table: MarkdownTable) -> None:
    """Test line with only a single pipe."""
    row = create_row_with_raw_line("|")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    assert positions == [0]


def test_only_escaped_pipe_single(basic_table: MarkdownTable) -> None:
    """Test line with only a single escaped pipe."""
    row = create_row_with_raw_line(r"\|")
    validator = TableValidator(basic_table)
    positions = validator._get_actual_pipe_positions(row)
    assert positions == []
