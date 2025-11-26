# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Fixer for markdown table formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from .models import MarkdownTable, TableFix, TableRow
from .table_validator import TableValidator


class TableFixer:
    """Fix markdown table formatting issues."""

    def __init__(self, table: MarkdownTable, max_line_length: int = 80):
        """Initialize fixer with a table.

        Args:
            table: The table to fix
            max_line_length: Maximum line length before adding MD013 disable
        """
        self.table = table
        self.max_line_length = max_line_length

    def fix(self) -> TableFix | None:
        """Fix the table formatting.

        Returns:
            TableFix if changes were made, None otherwise
        """
        # First validate to find violations
        validator = TableValidator(self.table)
        violations = validator.validate()

        if not violations:
            return None

        # Generate fixed table content
        fixed_lines = self._generate_fixed_table()

        # Get original content
        original_lines = [row.raw_line for row in self.table.rows]
        original_content = "\n".join(original_lines)
        fixed_content = "\n".join(fixed_lines)

        if original_content == fixed_content:
            return None

        return TableFix(
            file_path=self.table.file_path,
            start_line=self.table.start_line,
            end_line=self.table.end_line,
            original_content=original_content,
            fixed_content=fixed_content,
            violations_fixed=violations,
        )

    def _generate_fixed_table(self) -> list[str]:
        """Generate properly formatted table lines.

        Returns:
            List of fixed table lines
        """
        if not self.table.rows:
            return []

        # Calculate column widths
        column_widths = self._calculate_column_widths()

        # Generate each row
        fixed_lines: list[str] = []
        for row in self.table.rows:
            if row.is_separator:
                fixed_line = self._format_separator_row(row, column_widths)
            else:
                fixed_line = self._format_data_row(row, column_widths)
            fixed_lines.append(fixed_line)

        return fixed_lines

    def _calculate_column_widths(self) -> list[int]:
        """Calculate the maximum width needed for each column.

        Returns:
            List of column widths
        """
        if not self.table.rows:
            return []

        # Get max column count
        max_cols = max(len(row.cells) for row in self.table.rows)

        widths: list[int] = []
        for col_idx in range(max_cols):
            max_width = 0
            for row in self.table.rows:
                if col_idx < len(row.cells):
                    cell = row.cells[col_idx]
                    # For separator rows, use minimum width
                    if row.is_separator:
                        content_width = 3  # Minimum "---"
                    else:
                        content_width = len(cell.content.strip())
                    max_width = max(max_width, content_width)
            widths.append(max_width)

        return widths

    def _format_data_row(self, row: TableRow, column_widths: list[int]) -> str:
        """Format a data row with proper spacing and alignment.

        Args:
            row: The row to format
            column_widths: Width of each column

        Returns:
            Formatted row string
        """
        parts: list[str] = []

        for idx, cell in enumerate(row.cells):
            content = cell.content.strip()
            width = (
                column_widths[idx] if idx < len(column_widths) else len(content)
            )

            # Pad content to column width
            padded = content.ljust(width)
            parts.append(f" {padded} ")

        return "|" + "|".join(parts) + "|"

    def _format_separator_row(
        self, row: TableRow, column_widths: list[int]
    ) -> str:
        """Format a separator row with proper dashes and alignment.

        Args:
            row: The separator row to format
            column_widths: Width of each column

        Returns:
            Formatted separator row string
        """
        parts: list[str] = []

        for idx, cell in enumerate(row.cells):
            width = column_widths[idx] if idx < len(column_widths) else 3

            # Check for alignment indicators (: at start/end)
            content = cell.content.strip()
            left_align = content.startswith(":")
            right_align = content.endswith(":")

            # Generate separator with proper alignment indicators
            if left_align and right_align:
                # Center align
                separator = ":" + "-" * (width - 2) + ":"
            elif left_align:
                # Left align
                separator = ":" + "-" * (width - 1)
            elif right_align:
                # Right align
                separator = "-" * (width - 1) + ":"
            else:
                # Default (left align in most renderers)
                separator = "-" * width

            parts.append(f" {separator} ")

        return "|" + "|".join(parts) + "|"


class FileFixer:
    """Fix all tables in a markdown file."""

    def __init__(self, file_path: Path, max_line_length: int = 80):
        """Initialize fixer with file path.

        Args:
            file_path: Path to the markdown file
            max_line_length: Maximum line length before adding MD013 disable
        """
        self.file_path = file_path
        self.max_line_length = max_line_length

    def fix_file(
        self, tables: list[MarkdownTable], dry_run: bool = False
    ) -> list[TableFix]:
        """Fix all tables in the file.

        Args:
            tables: List of tables to fix
            dry_run: If True, don't write changes to file

        Returns:
            List of fixes applied
        """
        fixes: list[TableFix] = []

        for table in tables:
            fixer = TableFixer(table, self.max_line_length)
            fix = fixer.fix()
            if fix:
                fixes.append(fix)

        if not dry_run:
            # Apply fixes and add MD013 comments for all tables
            # (even if no fixes, we may still need MD013 comments)
            self._apply_fixes(fixes, tables)

        return fixes

    def _apply_fixes(
        self, fixes: list[TableFix], all_tables: list[MarkdownTable]
    ) -> None:
        """Apply fixes to the file and add MD013 comments where needed.

        Args:
            fixes: List of fixes to apply
            all_tables: All tables in the file (for checking line lengths)
        """
        # Read the entire file
        with open(self.file_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Build a map of all tables that need MD013 comments
        tables_needing_md013: dict[int, tuple[MarkdownTable, list[str]]] = {}

        # Check all tables for line length violations (not just fixed ones)
        for table in all_tables:
            # Get the table content (either fixed or original)
            table_lines = []
            fix_for_table = None
            for fix in fixes:
                if (
                    fix.start_line == table.start_line
                    and fix.end_line == table.end_line
                ):
                    fix_for_table = fix
                    table_lines = fix.fixed_content.split("\n")
                    break

            # If no fix, use original lines
            if not fix_for_table:
                table_lines = [row.raw_line for row in table.rows]

            # Check if any line exceeds max_line_length
            max_len = (
                max(len(line.rstrip()) for line in table_lines)
                if table_lines
                else 0
            )
            needs_md013 = max_len > self.max_line_length

            if needs_md013:
                tables_needing_md013[table.start_line] = (table, table_lines)

        # Create a unified list of all table modifications to apply
        # This includes both fixes and MD013-only tables
        all_modifications: list[tuple[int, int, list[str], bool]] = []

        # Add fixes to modifications list
        for fix in fixes:
            fixed_lines = fix.fixed_content.split("\n")
            needs_md013 = fix.start_line in tables_needing_md013
            all_modifications.append(
                (fix.start_line, fix.end_line, fixed_lines, needs_md013)
            )

        # Add tables that need MD013 but have no fixes
        for start_line, (table, table_lines) in tables_needing_md013.items():
            # Check if already in fixes
            if not any(mod[0] == start_line for mod in all_modifications):
                all_modifications.append(
                    (table.start_line, table.end_line, table_lines, True)
                )

        # Apply all modifications in reverse order to maintain line numbers
        # (only if there are modifications to apply)
        if not all_modifications:
            return

        for start_line, end_line, content_lines, needs_md013 in sorted(
            all_modifications, key=lambda x: x[0], reverse=True
        ):
            start_idx = start_line - 1
            end_idx = end_line

            # Prepare the lines to insert
            new_lines = [line + "\n" for line in content_lines]

            # Add MD013 comments if needed
            if needs_md013:
                # Check if disable comment already exists within 3 lines before the table
                has_disable = False
                check_start = max(0, start_idx - 3)
                for i in range(check_start, start_idx):
                    if "markdownlint-disable MD013" in lines[i]:
                        has_disable = True
                        break

                # Check if enable comment already exists within 3 lines after the table
                has_enable = False
                check_end = min(len(lines), end_idx + 3)
                for i in range(end_idx, check_end):
                    if "markdownlint-enable MD013" in lines[i]:
                        has_enable = True
                        break

                # Add disable comment if not present
                if not has_disable:
                    # Check for blank line before table
                    if start_idx > 0 and lines[start_idx - 1].strip():
                        # No blank line, add both blank line and comment
                        new_lines.insert(0, "\n")
                        new_lines.insert(
                            1, "<!-- markdownlint-disable MD013 -->\n"
                        )
                        new_lines.insert(2, "\n")
                    else:
                        # Blank line exists, just add comment
                        new_lines.insert(
                            0, "<!-- markdownlint-disable MD013 -->\n"
                        )
                        new_lines.insert(1, "\n")

                # Add enable comment if not present
                if not has_enable:
                    # Always add blank line and enable comment
                    new_lines.append("\n")
                    new_lines.append("<!-- markdownlint-enable MD013 -->\n")

            # Replace the section
            lines[start_idx:end_idx] = new_lines

        # Write back to file
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
