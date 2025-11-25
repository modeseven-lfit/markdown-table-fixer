# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test Unicode character width handling, especially emojis."""

from pathlib import Path

import pytest

from markdown_table_fixer.models import TableCell
from markdown_table_fixer.table_fixer import TableFixer


def test_emoji_display_width():
    """Test that emojis are counted as 2 characters wide."""
    # Emoji is 1 character in len() but displays as 2 characters wide
    cell_with_emoji = TableCell(content="✅", start_col=0, end_col=3)
    assert len("✅") == 1  # String length
    assert cell_with_emoji.display_width == 2  # Display width


def test_regular_text_display_width():
    """Test that regular ASCII text width matches length."""
    cell = TableCell(content="Hello", start_col=0, end_col=5)
    assert cell.display_width == 5


def test_mixed_emoji_text_display_width():
    """Test mixed emoji and text."""
    cell = TableCell(content="✅ Passed", start_col=0, end_col=9)
    # ✅ (2) + space (1) + Passed (6) = 9
    assert cell.display_width == 9


def test_multiple_emojis_display_width():
    """Test multiple emojis."""
    cell = TableCell(content="✅ ❌", start_col=0, end_col=5)
    # ✅ (2) + space (1) + ❌ (2) = 5
    assert cell.display_width == 5


def test_cell_with_whitespace():
    """Test that whitespace is properly stripped."""
    cell = TableCell(content="  ✅ Test  ", start_col=0, end_col=11)
    # After strip: ✅ (2) + space (1) + Test (4) = 7
    assert cell.display_width == 7


@pytest.mark.skip(
    reason="Test uses outdated API - needs rewrite for current TableFixer"
)
def test_table_with_emojis_alignment(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Test that tables with emojis are properly aligned."""
    markdown_content = """
| Feature | Status |
|---------|--------|
| JSON    | ✅ Yes  |
| YAML    | ✅ Yes  |
| XML     | ❌ No   |
"""

    test_file = tmp_path / "test_emoji.md"
    test_file.write_text(markdown_content.strip())

    fixer = TableFixer(test_file)  # type: ignore[arg-type]
    result = fixer.fix_tables()  # type: ignore[attr-defined]

    # Should fix the table
    assert result.tables_found == 1

    # Read the fixed content
    fixed_content = test_file.read_text()
    lines = fixed_content.split("\n")

    # All data rows should have pipes at the same columns
    data_rows = [lines[2], lines[3], lines[4]]

    # Extract pipe positions for each row
    pipe_positions = []
    for row in data_rows:
        positions = [i for i, char in enumerate(row) if char == "|"]
        pipe_positions.append(positions)

    # All rows should have pipes at the same positions
    assert pipe_positions[0] == pipe_positions[1] == pipe_positions[2], (
        f"Pipes not aligned:\n"
        f"Row 1: {pipe_positions[0]}\n"
        f"Row 2: {pipe_positions[1]}\n"
        f"Row 3: {pipe_positions[2]}\n"
        f"Content:\n{fixed_content}"
    )


@pytest.mark.skip(
    reason="Test uses outdated API - needs rewrite for current TableFixer"
)
def test_complex_emoji_table(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Test a more complex table with various emojis."""
    markdown_content = """
| Tool | Purpose | Status |
|------|---------|--------|
| `jq` | JSON parsing | ✅ Available |
| `yq` | YAML parsing | ⚠️ Needs install |
| `sed` | Text editing | ✅ Built-in |
"""

    test_file = tmp_path / "test_complex.md"
    test_file.write_text(markdown_content.strip())

    fixer = TableFixer(test_file)  # type: ignore[arg-type]
    result = fixer.fix_tables()  # type: ignore[attr-defined]

    assert result.tables_found == 1

    # Read the fixed content
    fixed_content = test_file.read_text()
    lines = fixed_content.split("\n")

    # Check that all rows have the same number of pipes
    for i, line in enumerate(lines, start=1):
        if line.strip():
            pipe_count = line.count("|")
            # Should have 4 pipes (3 columns = 4 pipes including borders)
            assert pipe_count == 4, f"Line {i} has {pipe_count} pipes: {line}"

    # Extract pipe positions for data rows
    data_rows = [lines[2], lines[3], lines[4]]
    pipe_positions = []
    for row in data_rows:
        positions = [i for i, char in enumerate(row) if char == "|"]
        pipe_positions.append(positions)

    # All rows should have pipes at the same positions
    assert pipe_positions[0] == pipe_positions[1] == pipe_positions[2], (
        f"Pipes not aligned in complex table:\n{fixed_content}"
    )


def test_emoji_with_code_blocks():
    """Test that emojis work correctly with code blocks."""
    cell = TableCell(content="✅ `metadata_json`", start_col=0, end_col=20)
    # ✅ (2) + space (1) + `metadata_json` (15) = 18
    assert cell.display_width == 18


def test_various_unicode_characters():
    """Test various Unicode characters that have different widths."""
    test_cases = [
        ("★", 1),  # Black star - narrow (wcwidth returns 1)
        ("→", 1),  # Rightwards arrow - narrow
        ("中文", 4),  # Chinese characters - 2 each
        ("Hello", 5),  # Regular ASCII
        ("café", 4),  # With accented character
        ("🚀", 2),  # Rocket emoji
    ]

    for content, expected_width in test_cases:
        cell = TableCell(content=content, start_col=0, end_col=len(content))
        assert cell.display_width == expected_width, (
            f"'{content}' should have display width {expected_width}, "
            f"got {cell.display_width}"
        )


def test_non_printable_characters_fallback():
    """Test that non-printable characters fall back to len()."""
    # Control characters and other non-printable characters
    # wcwidth.wcswidth returns -1 for these
    cell = TableCell(content="\x00\x01\x02", start_col=0, end_col=3)
    # Should fall back to len()
    assert cell.display_width == 3
