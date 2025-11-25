# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Command-line interface for markdown-table-fixer."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import sys
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
import typer

from ._version import __version__
from .exceptions import (
    FileAccessError,
    TableParseError,
)
from .github_client import GitHubClient
from .models import FileResult, OutputFormat, ScanResult
from .pr_fixer import PRFixer
from .pr_scanner import PRScanner
from .table_fixer import FileFixer
from .table_parser import MarkdownFileScanner, TableParser
from .table_validator import TableValidator

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"🏷️  markdown-table-fixer version {__version__}")
        raise typer.Exit()


class CustomTyper(typer.Typer):  # type: ignore[misc]
    """Custom Typer class that shows version in help."""

    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Check if help is being requested
        if "--help" in sys.argv or "-h" in sys.argv:
            console.print(f"🏷️  markdown-table-fixer version {__version__}\n")
        return super().__call__(*args, **kwargs)


app = CustomTyper(
    name="markdown-table-fixer",
    help="Markdown table formatter and linter with GitHub integration",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback()  # type: ignore[misc]
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Markdown table formatter and linter with GitHub integration."""
    pass


def setup_logging(
    log_level: str = "INFO", quiet: bool = False, verbose: bool = False
) -> None:
    """Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        quiet: Suppress all output except errors
        verbose: Enable verbose output
    """
    # Determine level from flags and option
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)

    # Get root logger and set its level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our handler
    rich_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
    )
    rich_handler.setLevel(level)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(rich_handler)


@app.command()  # type: ignore[misc]
def lint(
    path: Path = typer.Argument(
        Path("."),
        help="Path to scan for markdown files",
        exists=True,
    ),
    auto_fix: bool = typer.Option(
        True,
        "--auto-fix/--no-auto-fix",
        help="Automatically fix issues found (default: enabled)",
    ),
    fail_on_error: bool = typer.Option(
        True,
        "--fail-on-error/--no-fail-on-error",
        help="Exit with error code if validation failures found",
    ),
    parallel: bool = typer.Option(
        True,
        "--parallel/--no-parallel",
        help="Enable parallel processing (default: enabled)",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-j",
        min=1,
        max=32,
        help="Number of parallel workers (default: 4)",
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format (text, json) [default: text]",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Set logging level [default: INFO]",
        case_sensitive=False,
    ),
    max_line_length: int = typer.Option(
        80,
        "--max-line-length",
        "-l",
        help="Maximum line length before adding markdownlint MD013 disable",
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Scan markdown files for table formatting issues.

    Scans the specified path (file or directory) for markdown files
    containing tables with formatting issues. Can automatically fix
    issues or just report them.
    """
    setup_logging(log_level=log_level, quiet=quiet, verbose=verbose)

    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError as err:
        console.print(
            f"[red]Error:[/red] Invalid format '{output_format}'. "
            "Use 'text' or 'json'"
        )
        raise typer.Exit(1) from err

    # Find markdown files
    scanner = MarkdownFileScanner(path)
    markdown_files = scanner.find_markdown_files()

    if not markdown_files:
        if not quiet:
            console.print(f"No markdown files found in {path}")
        raise typer.Exit(0)

    if not quiet and fmt != OutputFormat.JSON:
        console.print(f"🔍 Scanning {len(markdown_files)} markdown file(s)...")

    # Scan and optionally fix files
    scan_result = ScanResult()

    if parallel and len(markdown_files) > 1:
        # Process files in parallel using thread pool
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(
                    _process_file, file_path, auto_fix, max_line_length
                ): file_path
                for file_path in markdown_files
            }

            for future in as_completed(future_to_file):
                file_result = future.result()
                scan_result.add_file_result(file_result)
    else:
        # Process files sequentially
        for file_path in markdown_files:
            file_result = _process_file(file_path, auto_fix, max_line_length)
            scan_result.add_file_result(file_result)

    # Output results
    if fmt == OutputFormat.JSON:
        _output_json_results(scan_result)
    else:
        _output_text_results(scan_result, quiet)

    # Exit with appropriate code
    if fail_on_error and scan_result.files_with_issues > 0:
        if (
            auto_fix
            and scan_result.files_fixed == scan_result.files_with_issues
        ):
            # All issues were fixed, exit success
            raise typer.Exit(0)
        else:
            # Issues remain unfixed
            raise typer.Exit(1)


@app.command()  # type: ignore[misc]
def github(
    target: str = typer.Argument(
        ...,
        help="GitHub organization name/URL or PR URL (e.g., https://github.com/org or https://github.com/owner/repo/pull/123)",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        "-t",
        help="GitHub token (or set GITHUB_TOKEN env var)",
        envvar="GITHUB_TOKEN",
    ),
    auto_fix: bool = typer.Option(
        True,
        "--auto-fix/--no-auto-fix",
        help="Automatically fix issues found (default: enabled)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying them",
    ),
    include_drafts: bool = typer.Option(
        False,
        "--include-drafts",
        help="Include draft PRs in scan",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-j",
        min=1,
        max=32,
        help="Number of parallel workers (default: 4)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Set logging level [default: INFO]",
        case_sensitive=False,
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Fix markdown tables in GitHub PRs.

    Can process either:
    - An entire organization (scans all PRs for table issues)
    - A specific PR by URL

    Examples:
      markdown-table-fixer github myorg --token ghp_xxx
      markdown-table-fixer github https://github.com/owner/repo/pull/123
    """
    setup_logging(log_level=log_level, quiet=quiet, verbose=verbose)

    if not token:
        console.print(
            "[red]Error:[/red] GitHub token required. "
            "Set GITHUB_TOKEN env var or use --token"
        )
        raise typer.Exit(1)

    # Detect if target is a PR URL or organization
    if "github.com" in target and "/pull/" in target:
        # Process single PR
        asyncio.run(
            _fix_single_pr(
                target,
                token,
                auto_fix=auto_fix,
                dry_run=dry_run,
                quiet=quiet,
            )
        )
    else:
        # Scan organization
        asyncio.run(
            _scan_organization(
                target,
                token,
                auto_fix=auto_fix,
                dry_run=dry_run,
                include_drafts=include_drafts,
                workers=workers,
                quiet=quiet,
            )
        )


async def _fix_single_pr(
    pr_url: str,
    token: str,
    auto_fix: bool = True,
    dry_run: bool = False,
    quiet: bool = False,
) -> None:
    """Fix a single PR by URL."""
    if not quiet:
        console.print(f"🔍 Analyzing PR: {pr_url}")

    try:
        async with GitHubClient(token) as client:  # type: ignore[attr-defined]
            fixer = PRFixer(client)
            result = await fixer.fix_pr_by_url(  # type: ignore[attr-defined]
                pr_url, dry_run=dry_run or not auto_fix
            )

            if result.success:
                if dry_run:
                    console.print(
                        f"\n[yellow]Would fix {len(result.files_modified)} file(s) in PR[/yellow]"
                    )
                elif auto_fix:
                    console.print(
                        f"\n[green]✅ Fixed {len(result.files_modified)} file(s) in PR[/green]"
                    )
                else:
                    console.print(
                        f"\n[yellow]Found issues in {len(result.files_modified)} file(s)[/yellow]"
                    )
            else:
                console.print(f"\n[red]Error:[/red] {result.message}")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error processing PR:[/red] {e}")
        raise typer.Exit(1) from e


async def _scan_organization(
    org: str,
    token: str,
    auto_fix: bool = True,
    dry_run: bool = False,
    include_drafts: bool = False,
    workers: int = 4,
    quiet: bool = False,
) -> None:
    """Scan organization for PRs with markdown table issues."""
    # Remove github.com prefix if present
    if "github.com" in org:
        org = org.split("github.com/")[-1].strip("/")

    if not quiet:
        console.print(f"🔍 Scanning organization: {org}")

    try:
        async with GitHubClient(token) as client:  # type: ignore[attr-defined]
            scanner = PRScanner(client)
            scan_result = await scanner.scan_organization(  # type: ignore[misc]
                org, include_drafts=include_drafts
            )

            if not quiet:
                console.print(
                    f"\n📊 Found {scan_result.total_prs} PRs in {scan_result.repositories_scanned} repositories"
                )
                console.print(
                    f"   {len(scan_result.blocked_prs)} PRs with markdown table issues"
                )

            if not scan_result.blocked_prs:
                console.print(
                    "\n[green]✅ No markdown table issues found![/green]"
                )
                return

            # Fix PRs if requested
            if auto_fix and not dry_run:
                if not quiet:
                    console.print(
                        f"\n🔧 Fixing {len(scan_result.blocked_prs)} PRs..."
                    )

                fixer = PRFixer(client)
                prs_fixed = 0

                # Process PRs in parallel
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = []
                    for blocked_pr in scan_result.blocked_prs:
                        if blocked_pr.has_markdown_issues:
                            future = executor.submit(
                                asyncio.run,
                                fixer.fix_pr(  # type: ignore[attr-defined]
                                    blocked_pr.pr_info, dry_run=dry_run
                                ),
                            )
                            futures.append(future)

                    for future in as_completed(futures):
                        result = future.result()
                        if result.success:
                            prs_fixed += 1

                console.print(f"\n[green]✅ Fixed {prs_fixed} PR(s)[/green]")

    except Exception as e:
        console.print(f"[red]Error scanning organization:[/red] {e}")
        raise typer.Exit(1) from e


def _process_file(
    file_path: Path, fix: bool = False, max_line_length: int = 80
) -> FileResult:
    """Process a single markdown file.

    Args:
        file_path: Path to the file
        fix: Whether to fix issues
        max_line_length: Maximum line length before adding MD013 disable

    Returns:
        File processing result
    """
    result = FileResult(file_path=file_path)

    try:
        # Parse tables from file
        parser = TableParser(file_path)
        tables = parser.parse_file()

        result.tables_found = len(tables)

        # Validate each table
        for table in tables:
            validator = TableValidator(table)
            violations = validator.validate()
            result.violations.extend(violations)

        # Fix if requested
        if fix:
            fixer = FileFixer(file_path, max_line_length=max_line_length)
            fixes = fixer.fix_file(tables, dry_run=False)
            result.fixes_applied = fixes

    except TableParseError as e:
        result.error = f"Parse error: {e}"
    except FileAccessError as e:
        result.error = f"Access error: {e}"
    except Exception as e:
        result.error = f"Unexpected error: {e}"

    return result


def _output_text_results(result: ScanResult, quiet: bool) -> None:
    """Output results in text format.

    Args:
        result: Scan results
        quiet: Whether to minimize output
    """
    if quiet:
        if result.files_with_issues > 0:
            console.print(f"Found issues in {result.files_with_issues} file(s)")
        return

    console.print("\n" + "=" * 70)
    console.print("📊 Scan Results")
    console.print("=" * 70)

    # Summary table
    summary_table = Table(title="Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="magenta")

    summary_table.add_row("Files scanned", str(result.files_scanned))
    summary_table.add_row("Files with issues", str(result.files_with_issues))
    summary_table.add_row("Total violations", str(result.total_violations))

    if result.files_fixed > 0:
        summary_table.add_row("Files fixed", str(result.files_fixed))
        summary_table.add_row("Fixes applied", str(result.total_fixes))

    console.print(summary_table)

    # Files with issues
    if result.files_with_issues > 0:
        files_table = Table(title="Files with Issues", show_header=True)
        files_table.add_column("File", style="cyan")
        files_table.add_column("Tables", style="magenta")
        files_table.add_column("Violations", style="yellow")
        files_table.add_column("Status", style="green")

        for file_result in result.file_results:
            if file_result.has_violations or file_result.error:
                status = (
                    "✅ Fixed"
                    if file_result.was_fixed
                    else ("❌ Error" if file_result.error else "⚠️  Issues")
                )
                files_table.add_row(
                    str(file_result.file_path.name),
                    str(file_result.tables_found),
                    str(len(file_result.violations)),
                    status,
                )

        console.print(files_table)

        # Show detailed violations for first few files
        console.print("\n📋 Detailed Violations:\n")
        for file_result in result.file_results[:3]:
            if file_result.has_violations:
                console.print(f"{file_result.file_path}")
                for _i, violation in enumerate(file_result.violations[:5]):
                    console.print(f"  {violation.message}")
                if len(file_result.violations) > 5:
                    console.print(
                        f"  ... and {len(file_result.violations) - 5} more violations"
                    )
                console.print()

    # Final message
    if result.files_fixed > 0:
        console.print(f"✅ Fixed {result.files_fixed} file(s)!")
    elif result.files_with_issues > 0:
        console.print("⚠️  Run with --auto-fix to automatically fix issues")
    else:
        console.print("✅ No issues found!")


def _output_json_results(result: ScanResult) -> None:
    """Output results in JSON format.

    Args:
        result: Scan results
    """
    output: dict[str, Any] = {
        "files_scanned": result.files_scanned,
        "files_with_issues": result.files_with_issues,
        "files_fixed": result.files_fixed,
        "total_violations": result.total_violations,
        "total_fixes": result.total_fixes,
        "files": [],
    }

    for file_result in result.file_results:
        file_data: dict[str, Any] = {
            "path": str(file_result.file_path),
            "tables_found": file_result.tables_found,
            "violations": len(file_result.violations),
            "fixes_applied": len(file_result.fixes_applied),
            "error": file_result.error,
        }

        if file_result.violations:
            file_data["violation_details"] = [
                {
                    "type": v.violation_type.value,
                    "line": v.line_number,
                    "column": v.column,
                    "message": v.message,
                }
                for v in file_result.violations
            ]

        output["files"].append(file_data)

    console.print(json.dumps(output, indent=2))


if __name__ == "__main__":
    app()
