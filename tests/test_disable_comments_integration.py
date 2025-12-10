# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Integration tests for markdownlint disable/enable comments across code paths."""

from pathlib import Path

from markdown_table_fixer.cli import _process_file
from markdown_table_fixer.pr_fixer import PRFixer
from markdown_table_fixer.table_parser import TableParser


def test_lint_respects_disable_comments(tmp_path: Path) -> None:
    """Test that lint command respects disable comments."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

## Table 1 - No Disable
| Col1 | Col2 |
|---|---|
|A|B|

## Table 2 - MD060 Disabled
<!-- markdownlint-disable MD060 -->
| Col1 | Col2 |
|---|---|
|A|B|
<!-- markdownlint-enable MD060 -->
"""
    )

    # Process file without fixing
    result = _process_file(test_file, fix=False, max_line_length=80)

    # Should only report violations from Table 1
    # Table 2 violations should be filtered out
    assert len(result.violations) == 12  # Only from Table 1
    for v in result.violations:
        # All remaining violations should be from lines 4-6 (Table 1)
        assert v.line_number in [4, 5, 6]


def test_lint_respects_md013_disable(tmp_path: Path) -> None:
    """Test that lint respects MD013 disable comments."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

## Table 1 - Long Line
| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 | Column 7 | Column 8 | Column 9 | Column 10 |
| -------- | -------- | -------- | -------- | -------- | -------- | -------- | -------- | -------- | --------- |

## Table 2 - Long Line with MD013 Disabled
<!-- markdownlint-disable MD013 -->
| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 | Column 7 | Column 8 | Column 9 | Column 10 |
| -------- | -------- | -------- | -------- | -------- | -------- | -------- | -------- | -------- | --------- |
<!-- markdownlint-enable MD013 -->
"""
    )

    # Process file with MD013 checking
    result = _process_file(test_file, fix=False, max_line_length=80)

    # Should only report MD013 violations from Table 1
    md013_violations = [v for v in result.violations if v.md_rule == "MD013"]
    assert len(md013_violations) == 2  # Only from Table 1 (header + separator)

    # All MD013 violations should be from Table 1 (lines 4-5)
    for v in md013_violations:
        assert v.line_number in [4, 5]


def test_lint_respects_multiple_disable_blocks(tmp_path: Path) -> None:
    """Test that lint respects multiple disable/enable blocks."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

<!-- markdownlint-disable MD060 -->
|A|B|
|--|--|
|1|2|
<!-- markdownlint-enable MD060 -->

Some text

<!-- markdownlint-disable MD060 -->
|C|D|
|--|--|
|3|4|
<!-- markdownlint-enable MD060 -->

After disable

|E|F|
|--|--|
|5|6|
"""
    )

    result = _process_file(test_file, fix=False, max_line_length=80)

    # Should only report violations from the last table (not in disable block)
    assert len(result.violations) > 0
    for v in result.violations:
        # All violations should be from the last table (lines 19-21)
        assert v.line_number in [19, 20, 21]


def test_lint_cumulative_disables(tmp_path: Path) -> None:
    """Test that disable comments are cumulative."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

<!-- markdownlint-disable MD013 -->
Line 4
<!-- markdownlint-disable MD060 -->
|A|B|
Line 7
<!-- markdownlint-enable MD013 -->
|C|D|
<!-- markdownlint-enable MD060 -->
|E|F|
"""
    )

    result = _process_file(test_file, fix=False, max_line_length=10)

    # Line 6: Both MD013 and MD060 disabled
    # Line 9: Only MD060 disabled (MD013 enabled)
    # Line 11: Both enabled

    violations_by_line: dict[int, list[str]] = {}
    for v in result.violations:
        if v.line_number not in violations_by_line:
            violations_by_line[v.line_number] = []
        violations_by_line[v.line_number].append(v.md_rule)

    # Line 6 should have no violations (both disabled)
    assert 6 not in violations_by_line

    # Line 9 should have MD013 violations only (MD060 still disabled)
    if 9 in violations_by_line:
        assert all(rule == "MD013" for rule in violations_by_line[9])

    # Line 11 should have both MD013 and MD060 violations
    assert 11 in violations_by_line
    rules_at_11 = set(violations_by_line[11])
    assert "MD060" in rules_at_11  # Table formatting issues


def test_pr_fixer_check_respects_disable_comments(tmp_path: Path) -> None:
    """Test that PRFixer._check_table_needs_fixes respects disable comments."""
    # Create a test file with disabled section
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

<!-- markdownlint-disable MD013 MD060 -->
| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 | Column 7 | Column 8 | Column 9 | Column 10 |
|---|---|---|---|---|---|---|---|---|---|
| Value 1  | Value 2  | Value 3  | Value 4  | Value 5  | Value 6  | Value 7  | Value 8  | Value 9  | Value 10  |
<!-- markdownlint-enable MD013 MD060 -->
"""
    )

    # Parse the table
    parser = TableParser(test_file)
    tables = parser.parse_file()
    assert len(tables) == 1

    # Create PRFixer instance (we don't need a real client for this test)
    # We'll directly call _check_table_needs_fixes
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    pr_fixer = PRFixer(mock_client)

    # Check if table needs fixes
    has_validation_issues, needs_md013 = pr_fixer._check_table_needs_fixes(
        tables[0], max_line_length=80
    )

    # Should report no validation issues because rules are disabled
    assert not has_validation_issues


def test_pr_fixer_check_partial_disable(tmp_path: Path) -> None:
    """Test PRFixer with only MD013 disabled (MD060 still active)."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

<!-- markdownlint-disable MD013 -->
| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 | Column 6 | Column 7 | Column 8 | Column 9 | Column 10 |
|---|---|---|---|---|---|---|---|---|---|
<!-- markdownlint-enable MD013 -->
"""
    )

    parser = TableParser(test_file)
    tables = parser.parse_file()
    assert len(tables) == 1

    from unittest.mock import MagicMock

    mock_client = MagicMock()
    pr_fixer = PRFixer(mock_client)

    has_validation_issues, needs_md013 = pr_fixer._check_table_needs_fixes(
        tables[0], max_line_length=80
    )

    # Should report validation issues because MD060 is not disabled
    # (missing spaces in table cells)
    assert has_validation_issues


def test_disable_comment_filtering_consistency(tmp_path: Path) -> None:
    """Test that lint and PRFixer produce consistent results."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

<!-- markdownlint-disable MD060 -->
|Name|Age|City|
|---|---|---|
|Alice|30|NYC|
|Bob|25|LA|
<!-- markdownlint-enable MD060 -->
"""
    )

    # Test with lint path
    lint_result = _process_file(test_file, fix=False, max_line_length=80)

    # Test with PRFixer path
    parser = TableParser(test_file)
    tables = parser.parse_file()

    from unittest.mock import MagicMock

    mock_client = MagicMock()
    pr_fixer = PRFixer(mock_client)

    has_validation_issues, _ = pr_fixer._check_table_needs_fixes(
        tables[0], max_line_length=80
    )

    # Both paths should agree: no MD060 violations because MD060 is disabled
    md060_violations = [
        v for v in lint_result.violations if v.md_rule == "MD060"
    ]
    assert len(md060_violations) == 0
    assert not has_validation_issues


def test_violation_reporting_with_disabled_rules(tmp_path: Path) -> None:
    """Test that get_violations_by_rule only includes non-disabled violations."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test

|A|B|
|--|--|
|1|2|

<!-- markdownlint-disable MD060 -->
|C|D|
|--|--|
|3|4|
<!-- markdownlint-enable MD060 -->
"""
    )

    result = _process_file(test_file, fix=False, max_line_length=80)
    rule_counts = result.get_violations_by_rule()

    # Should only count violations from first table
    assert "MD060" in rule_counts
    # Exact count will depend on validation logic, but should be > 0
    assert rule_counts["MD060"] > 0

    # All reported violations should be from lines 3-5 (first table)
    for v in result.violations:
        assert v.line_number in [3, 4, 5]
