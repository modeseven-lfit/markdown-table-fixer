# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Tests for violation reporting by markdownlint rule code."""

from pathlib import Path

from markdown_table_fixer.models import (
    FileResult,
    TableViolation,
    ViolationType,
)


def test_violation_type_to_md_rule() -> None:
    """Test that violation types map to correct MD rule codes."""
    # Table formatting violations should map to MD060
    assert ViolationType.MISALIGNED_PIPE.to_md_rule() == "MD060"
    assert ViolationType.MISSING_SPACE_LEFT.to_md_rule() == "MD060"
    assert ViolationType.MISSING_SPACE_RIGHT.to_md_rule() == "MD060"
    assert ViolationType.EXTRA_SPACE_LEFT.to_md_rule() == "MD060"
    assert ViolationType.EXTRA_SPACE_RIGHT.to_md_rule() == "MD060"
    assert ViolationType.INCONSISTENT_ALIGNMENT.to_md_rule() == "MD060"
    assert ViolationType.MALFORMED_SEPARATOR.to_md_rule() == "MD060"

    # Line length violations should map to MD013
    assert ViolationType.LINE_TOO_LONG.to_md_rule() == "MD013"


def test_table_violation_md_rule_property(tmp_path: Path) -> None:
    """Test that TableViolation has md_rule property."""
    test_file = tmp_path / "test.md"

    violation = TableViolation(
        violation_type=ViolationType.MISALIGNED_PIPE,
        line_number=1,
        column=10,
        message="Test violation",
        file_path=test_file,
        table_start_line=1,
    )

    assert violation.md_rule == "MD060"

    line_too_long = TableViolation(
        violation_type=ViolationType.LINE_TOO_LONG,
        line_number=1,
        column=0,
        message="Line too long",
        file_path=test_file,
        table_start_line=1,
    )

    assert line_too_long.md_rule == "MD013"


def test_file_result_get_violations_by_rule(tmp_path: Path) -> None:
    """Test FileResult.get_violations_by_rule() method."""
    test_file = tmp_path / "test.md"

    # Create file result with multiple violation types
    result = FileResult(file_path=test_file)

    # Add some MD060 violations (table formatting)
    result.violations.append(
        TableViolation(
            violation_type=ViolationType.MISALIGNED_PIPE,
            line_number=1,
            column=10,
            message="Misaligned pipe",
            file_path=test_file,
            table_start_line=1,
        )
    )
    result.violations.append(
        TableViolation(
            violation_type=ViolationType.MISSING_SPACE_LEFT,
            line_number=2,
            column=5,
            message="Missing space",
            file_path=test_file,
            table_start_line=1,
        )
    )
    result.violations.append(
        TableViolation(
            violation_type=ViolationType.INCONSISTENT_ALIGNMENT,
            line_number=3,
            column=0,
            message="Inconsistent alignment",
            file_path=test_file,
            table_start_line=1,
        )
    )

    # Add some MD013 violations (line length)
    result.violations.append(
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=1,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=1,
        )
    )
    result.violations.append(
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=2,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=1,
        )
    )

    # Get violations grouped by rule
    rule_counts = result.get_violations_by_rule()

    # Should have 3 MD060 and 2 MD013
    assert rule_counts == {"MD060": 3, "MD013": 2}


def test_file_result_get_violations_by_rule_empty(tmp_path: Path) -> None:
    """Test get_violations_by_rule() with no violations."""
    test_file = tmp_path / "test.md"
    result = FileResult(file_path=test_file)

    rule_counts = result.get_violations_by_rule()

    assert rule_counts == {}


def test_file_result_get_violations_by_rule_single_type(
    tmp_path: Path,
) -> None:
    """Test get_violations_by_rule() with only one rule type."""
    test_file = tmp_path / "test.md"
    result = FileResult(file_path=test_file)

    # Add only MD013 violations
    for i in range(5):
        result.violations.append(
            TableViolation(
                violation_type=ViolationType.LINE_TOO_LONG,
                line_number=i + 1,
                column=0,
                message="Line too long",
                file_path=test_file,
                table_start_line=1,
            )
        )

    rule_counts = result.get_violations_by_rule()

    assert rule_counts == {"MD013": 5}
