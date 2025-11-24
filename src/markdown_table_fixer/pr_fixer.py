# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Fixer for markdown tables in pull requests."""

from __future__ import annotations

from contextlib import suppress
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .github_client import GitHubClient

from .table_fixer import TableFixer
from .table_parser import TableParser
from .table_validator import TableValidator


class PRFixer:
    """Fix markdown tables in pull requests."""

    def __init__(self, client: GitHubClient):
        """Initialize PR fixer.

        Args:
            client: GitHub API client
        """
        self.client = client
        self.logger = logging.getLogger("markdown_table_fixer.pr_fixer")

    async def fix_pr_tables(
        self,
        owner: str,
        repo: str,
        pr: dict[str, Any],
        *,
        dry_run: bool = False,
        create_comment: bool = True,
    ) -> dict[str, Any]:
        """Fix markdown tables in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr: Pull request data
            dry_run: If True, don't actually push changes
            create_comment: If True, create a comment summarizing fixes

        Returns:
            Dictionary with fix results
        """
        pr_number = pr.get("number")
        branch = pr.get("head", {}).get("ref")
        head_sha = pr.get("head", {}).get("sha")

        self.logger.debug(f"PR #{pr_number}: branch={branch}, sha={head_sha}")

        if not pr_number or not branch or not head_sha:
            self.logger.error("Invalid PR data: missing required fields")
            return {
                "success": False,
                "error": "Invalid PR data",
                "files_fixed": 0,
                "tables_fixed": 0,
            }

        # Get markdown files from the PR
        self.logger.debug(f"Fetching files for PR #{pr_number}")
        files = await self.client.get_pr_files(owner, repo, pr_number)
        self.logger.debug(f"Found {len(files)} files in PR")
        markdown_files = [
            f
            for f in files
            if f.get("filename", "").endswith(".md")
            and f.get("status") != "removed"
        ]

        self.logger.debug(f"Found {len(markdown_files)} markdown files")
        for f in markdown_files:
            self.logger.debug(f"  - {f.get('filename')}")

        if not markdown_files:
            self.logger.info("No markdown files to fix")
            return {
                "success": True,
                "message": "No markdown files to fix",
                "files_fixed": 0,
                "tables_fixed": 0,
            }

        files_fixed = 0
        tables_fixed = 0
        fixed_files_list = []

        for file_data in markdown_files:
            filename = file_data.get("filename", "")
            file_sha = file_data.get("sha")

            self.logger.debug(f"Processing file: {filename}")

            if not filename or not file_sha:
                self.logger.warning("Skipping file with missing name or SHA")
                continue

            try:
                # Get current file content
                self.logger.debug(f"Fetching content for {filename}")
                content = await self.client.get_file_content(
                    owner, repo, filename, branch
                )
                self.logger.debug(f"Content length: {len(content)} bytes")

                # Parse and fix tables by splitting content into lines
                lines = content.splitlines(keepends=True)
                self.logger.debug(f"File has {len(lines)} lines")

                parser = TableParser(filename)
                tables = parser._find_and_parse_tables(lines)

                self.logger.debug(f"Found {len(tables)} tables in {filename}")

                if not tables:
                    self.logger.debug(f"No tables found in {filename}")
                    continue

                # Check if any tables have issues
                has_issues = False
                fixes_applied = 0

                for table in tables:
                    validator = TableValidator(table)
                    violations = validator.validate()

                    self.logger.debug(
                        f"Table at line {table.start_line}: {len(violations)} violations"
                    )

                    if violations:
                        has_issues = True
                        fixes_applied += 1

                if not has_issues:
                    self.logger.debug(f"No issues found in {filename}")
                    continue

                self.logger.info(f"Found issues in {filename}, applying fixes")

                # Apply fixes
                fixed_content = content
                for table in tables:
                    fixer = TableFixer(table)
                    fix = fixer.fix()

                    if fix:
                        fixed_content = fixed_content.replace(
                            fix.original_content, fix.fixed_content
                        )

                # Only update if content changed
                if fixed_content != content:
                    self.logger.debug(f"Content changed for {filename}")
                    if not dry_run:
                        self.logger.debug(
                            f"Updating file {filename} in branch {branch}"
                        )
                        # Re-fetch file info to get current SHA
                        file_info = await self.client._request(
                            "GET",
                            f"/repos/{owner}/{repo}/contents/{filename}",
                            params={"ref": branch},
                        )
                        current_sha_raw = (
                            file_info.get("sha")
                            if isinstance(file_info, dict)
                            else file_sha
                        )
                        current_sha = (
                            current_sha_raw
                            if isinstance(current_sha_raw, str)
                            else file_sha
                        )

                        # Update the file
                        commit_message = (
                            f"Fix markdown table formatting in {filename}\n\n"
                            f"Automatically fixed {fixes_applied} table(s) "
                            f"in PR #{pr_number}"
                        )

                        await self.client.update_file(
                            owner,
                            repo,
                            filename,
                            fixed_content,
                            commit_message,
                            branch,
                            current_sha,
                        )
                        self.logger.info(f"Successfully updated {filename}")

                    files_fixed += 1
                    tables_fixed += fixes_applied
                    fixed_files_list.append(
                        {"filename": filename, "tables": fixes_applied}
                    )
                else:
                    self.logger.debug(f"No content changes for {filename}")

            except Exception:
                # Continue with other files if one fails
                continue

        self.logger.info(
            f"PR fix complete: {files_fixed} files, {tables_fixed} tables"
        )

        # Create a comment if requested and fixes were made
        if create_comment and files_fixed > 0 and not dry_run:
            self.logger.debug("Creating PR comment")
            comment_body = self._generate_comment(
                files_fixed, tables_fixed, fixed_files_list
            )
            # Don't fail if comment creation fails
            with suppress(Exception):
                await self.client.create_comment(
                    owner, repo, pr_number, comment_body
                )

        return {
            "success": True,
            "files_fixed": files_fixed,
            "tables_fixed": tables_fixed,
            "fixed_files": fixed_files_list,
            "dry_run": dry_run,
        }

    def _generate_comment(
        self,
        files_fixed: int,
        tables_fixed: int,
        fixed_files: list[dict[str, Any]],
    ) -> str:
        """Generate a comment body for the PR.

        Args:
            files_fixed: Number of files fixed
            tables_fixed: Number of tables fixed
            fixed_files: List of fixed files with details

        Returns:
            Comment body text
        """
        lines = [
            "## 🛠️ Markdown Table Fixer",
            "",
            "Automatically fixed markdown table formatting issues:",
            f"- **{files_fixed}** file(s) updated",
            f"- **{tables_fixed}** table(s) fixed",
            "",
        ]

        if fixed_files:
            lines.append("### Files Updated:")
            for file_info in fixed_files:
                filename = file_info["filename"]
                table_count = file_info["tables"]
                lines.append(f"- `{filename}` - {table_count} table(s) fixed")
            lines.append("")

        lines.extend(
            [
                "---",
                "*This fix was automatically applied by "
                "[markdown-table-fixer](https://github.com/lfit/markdown-table-fixer)*",
            ]
        )

        return "\n".join(lines)
