# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Tests for rule disabler functionality."""

from pathlib import Path

from markdown_table_fixer.models import TableViolation, ViolationType
from markdown_table_fixer.rule_disabler import (
    DisabledRulesState,
    RuleDisabler,
    filter_violations_by_disabled_rules,
)


def test_disabled_rules_state_initial() -> None:
    """Test initial state has no disabled rules."""
    state = DisabledRulesState()
    assert not state.is_rule_disabled("MD013")
    assert not state.is_rule_disabled("MD060")
    assert state.disabled_rules == set()


def test_disabled_rules_state_disable() -> None:
    """Test disabling rules."""
    state = DisabledRulesState()
    state.disable_rules({"MD013"})
    assert state.is_rule_disabled("MD013")
    assert not state.is_rule_disabled("MD060")
    assert state.disabled_rules == {"MD013"}


def test_disabled_rules_state_disable_multiple() -> None:
    """Test disabling multiple rules."""
    state = DisabledRulesState()
    state.disable_rules({"MD013", "MD060"})
    assert state.is_rule_disabled("MD013")
    assert state.is_rule_disabled("MD060")
    assert state.disabled_rules == {"MD013", "MD060"}


def test_disabled_rules_state_enable() -> None:
    """Test enabling a disabled rule."""
    state = DisabledRulesState()
    state.disable_rules({"MD013", "MD060"})
    state.enable_rules({"MD013"})
    assert not state.is_rule_disabled("MD013")
    assert state.is_rule_disabled("MD060")
    assert state.disabled_rules == {"MD060"}


def test_disabled_rules_state_enable_all() -> None:
    """Test enabling all disabled rules."""
    state = DisabledRulesState()
    state.disable_rules({"MD013", "MD060"})
    state.enable_rules({"MD013", "MD060"})
    assert not state.is_rule_disabled("MD013")
    assert not state.is_rule_disabled("MD060")
    assert state.disabled_rules == set()


def test_disabled_rules_state_copy() -> None:
    """Test copying state."""
    state = DisabledRulesState()
    state.disable_rules({"MD013"})

    copy = state.copy()
    assert copy.disabled_rules == state.disabled_rules
    assert copy.disabled_rules is not state.disabled_rules

    # Modify copy shouldn't affect original
    copy.disable_rules({"MD060"})
    assert state.disabled_rules == {"MD013"}
    assert copy.disabled_rules == {"MD013", "MD060"}


def test_rule_disabler_parse_simple(tmp_path: Path) -> None:
    """Test parsing a file with simple disable/enable."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
Line 2
<!-- markdownlint-disable MD013 -->
Line 4
Line 5
<!-- markdownlint-enable MD013 -->
Line 7
"""
    )

    disabler = RuleDisabler(test_file)
    disabler.parse_file()

    # Before disable
    assert not disabler.is_rule_disabled_at_line(1, "MD013")
    assert not disabler.is_rule_disabled_at_line(2, "MD013")

    # After disable, before enable
    assert disabler.is_rule_disabled_at_line(3, "MD013")
    assert disabler.is_rule_disabled_at_line(4, "MD013")
    assert disabler.is_rule_disabled_at_line(5, "MD013")

    # After enable
    assert not disabler.is_rule_disabled_at_line(6, "MD013")
    assert not disabler.is_rule_disabled_at_line(7, "MD013")


def test_rule_disabler_parse_multiple_rules(tmp_path: Path) -> None:
    """Test parsing with multiple rules disabled."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
<!-- markdownlint-disable MD013 MD060 -->
Line 3
<!-- markdownlint-enable MD013 -->
Line 5
<!-- markdownlint-enable MD060 -->
Line 7
"""
    )

    disabler = RuleDisabler(test_file)
    disabler.parse_file()

    # Both disabled
    assert disabler.is_rule_disabled_at_line(3, "MD013")
    assert disabler.is_rule_disabled_at_line(3, "MD060")

    # Only MD060 disabled
    assert not disabler.is_rule_disabled_at_line(5, "MD013")
    assert disabler.is_rule_disabled_at_line(5, "MD060")

    # Both enabled
    assert not disabler.is_rule_disabled_at_line(7, "MD013")
    assert not disabler.is_rule_disabled_at_line(7, "MD060")


def test_rule_disabler_parse_nested_disable(tmp_path: Path) -> None:
    """Test that disable comments are cumulative."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
<!-- markdownlint-disable MD013 -->
Line 3
<!-- markdownlint-disable MD060 -->
Line 5
<!-- markdownlint-enable MD013 -->
Line 7
<!-- markdownlint-enable MD060 -->
Line 9
"""
    )

    disabler = RuleDisabler(test_file)
    disabler.parse_file()

    # Only MD013 disabled
    assert disabler.is_rule_disabled_at_line(3, "MD013")
    assert not disabler.is_rule_disabled_at_line(3, "MD060")

    # Both disabled
    assert disabler.is_rule_disabled_at_line(5, "MD013")
    assert disabler.is_rule_disabled_at_line(5, "MD060")

    # Only MD060 disabled
    assert not disabler.is_rule_disabled_at_line(7, "MD013")
    assert disabler.is_rule_disabled_at_line(7, "MD060")

    # Both enabled
    assert not disabler.is_rule_disabled_at_line(9, "MD013")
    assert not disabler.is_rule_disabled_at_line(9, "MD060")


def test_rule_disabler_get_disabled_rules(tmp_path: Path) -> None:
    """Test getting all disabled rules at a line."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
<!-- markdownlint-disable MD013 MD060 -->
Line 3
"""
    )

    disabler = RuleDisabler(test_file)
    disabler.parse_file()

    # No rules disabled at line 1
    assert disabler.get_disabled_rules_at_line(1) == set()

    # Both rules disabled at line 3
    assert disabler.get_disabled_rules_at_line(3) == {"MD013", "MD060"}


def test_rule_disabler_nonexistent_file(tmp_path: Path) -> None:
    """Test handling of nonexistent file."""
    test_file = tmp_path / "nonexistent.md"

    disabler = RuleDisabler(test_file)
    disabler.parse_file()

    # Should not crash, all rules should be enabled
    assert not disabler.is_rule_disabled_at_line(1, "MD013")
    assert not disabler.is_rule_disabled_at_line(100, "MD060")


def test_rule_disabler_lazy_parsing(tmp_path: Path) -> None:
    """Test that file is not parsed until needed."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")

    disabler = RuleDisabler(test_file)
    assert not disabler._parsed

    # First call should trigger parsing
    disabler.is_rule_disabled_at_line(1, "MD013")
    assert disabler._parsed


def test_filter_violations_empty_list(tmp_path: Path) -> None:
    """Test filtering empty violations list."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")

    violations: list[TableViolation] = []
    filtered = filter_violations_by_disabled_rules(violations, test_file)

    assert filtered == []


def test_filter_violations_no_disabled_rules(tmp_path: Path) -> None:
    """Test filtering when no rules are disabled."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
| A | B |
| - | - |
| 1 | 2 |
"""
    )

    violations = [
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=2,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=2,
        ),
        TableViolation(
            violation_type=ViolationType.MISALIGNED_PIPE,
            line_number=3,
            column=5,
            message="Misaligned",
            file_path=test_file,
            table_start_line=2,
        ),
    ]

    filtered = filter_violations_by_disabled_rules(violations, test_file)

    # All violations should remain
    assert len(filtered) == 2
    assert filtered == violations


def test_filter_violations_with_disabled_rules(tmp_path: Path) -> None:
    """Test filtering when rules are disabled."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
<!-- markdownlint-disable MD013 -->
| A | B |
| - | - |
| 1 | 2 |
<!-- markdownlint-enable MD013 -->
"""
    )

    violations = [
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=3,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=3,
        ),
        TableViolation(
            violation_type=ViolationType.MISALIGNED_PIPE,
            line_number=4,
            column=5,
            message="Misaligned",
            file_path=test_file,
            table_start_line=3,
        ),
    ]

    filtered = filter_violations_by_disabled_rules(violations, test_file)

    # Only MD060 violation should remain (MD013 is disabled)
    assert len(filtered) == 1
    assert filtered[0].violation_type == ViolationType.MISALIGNED_PIPE


def test_filter_violations_all_disabled(tmp_path: Path) -> None:
    """Test filtering when all rules are disabled."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
<!-- markdownlint-disable MD013 MD060 -->
| A | B |
| - | - |
| 1 | 2 |
"""
    )

    violations = [
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=3,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=3,
        ),
        TableViolation(
            violation_type=ViolationType.MISALIGNED_PIPE,
            line_number=4,
            column=5,
            message="Misaligned",
            file_path=test_file,
            table_start_line=3,
        ),
    ]

    filtered = filter_violations_by_disabled_rules(violations, test_file)

    # All violations should be filtered out
    assert len(filtered) == 0


def test_filter_violations_partial_disable(tmp_path: Path) -> None:
    """Test filtering when rules are disabled for part of the file."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        """# Test
| A | B |
<!-- markdownlint-disable MD013 -->
| C | D |
<!-- markdownlint-enable MD013 -->
| E | F |
"""
    )

    violations = [
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=2,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=2,
        ),
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=4,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=4,
        ),
        TableViolation(
            violation_type=ViolationType.LINE_TOO_LONG,
            line_number=6,
            column=0,
            message="Line too long",
            file_path=test_file,
            table_start_line=6,
        ),
    ]

    filtered = filter_violations_by_disabled_rules(violations, test_file)

    # Only violations at lines 2 and 6 should remain (line 4 has MD013 disabled)
    assert len(filtered) == 2
    assert filtered[0].line_number == 2
    assert filtered[1].line_number == 6
