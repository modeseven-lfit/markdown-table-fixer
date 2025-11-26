# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Fixer for markdown tables in pull requests."""

from __future__ import annotations

from contextlib import suppress
import logging
from pathlib import Path
import re
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .github_client import GitHubClient

from .models import GitHubFixResult, PRInfo
from .table_fixer import FileFixer, TableFixer
from .table_parser import MarkdownFileScanner, TableParser
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

    async def fix_pr_by_url(
        self,
        pr_url: str,
        *,
        sync_strategy: str = "none",
        conflict_strategy: str = "fail",
        dry_run: bool = False,
    ) -> GitHubFixResult:
        """Fix markdown tables in a PR by URL, amending the existing commit.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            sync_strategy: How to sync with base branch: 'none', 'rebase', or 'merge'
            conflict_strategy: How to resolve conflicts: 'fail', 'ours', or 'theirs'
            dry_run: If True, don't actually push changes

        Returns:
            GitHubFixResult with operation details
        """
        # Parse PR URL
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url
        )
        if not match:
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=0,
                    title="",
                    repository="",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=f"Invalid PR URL format: {pr_url}",
            )

        owner, repo, pr_number_str = match.groups()
        pr_number = int(pr_number_str)

        self.logger.debug(f"Processing PR: {owner}/{repo}#{pr_number}")

        try:
            # Get PR details
            pr_data = await self.client._request(
                "GET", f"/repos/{owner}/{repo}/pulls/{pr_number}"
            )

            if not isinstance(pr_data, dict):
                return GitHubFixResult(
                    pr_info=PRInfo(
                        number=pr_number,
                        title="",
                        repository=f"{owner}/{repo}",
                        url=pr_url,
                        author="",
                        is_draft=False,
                        head_ref="",
                        head_sha="",
                        base_ref="",
                        mergeable="",
                        merge_state_status="",
                    ),
                    success=False,
                    message="Failed to fetch PR data",
                )

            head = pr_data.get("head", {})
            head_sha = head.get("sha", "")
            head_ref = head.get("ref", "")
            head_repo = head.get("repo", {})
            clone_url = head_repo.get("clone_url", "")

            pr_info = PRInfo(
                number=pr_number,
                title=pr_data.get("title", ""),
                repository=f"{owner}/{repo}",
                url=pr_url,
                author=pr_data.get("user", {}).get("login", ""),
                is_draft=pr_data.get("draft", False),
                head_ref=head_ref,
                head_sha=head_sha,
                base_ref=pr_data.get("base", {}).get("ref", ""),
                mergeable=pr_data.get("mergeable", "unknown"),
                merge_state_status=pr_data.get("mergeable_state", "unknown"),
            )

            if not clone_url:
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message="PR head repository not accessible",
                )

            # Clone and fix using Git operations
            return await self._fix_pr_with_git(
                pr_info,
                clone_url,
                owner,
                repo,
                sync_strategy=sync_strategy,
                conflict_strategy=conflict_strategy,
                dry_run=dry_run,
            )

        except Exception as e:
            self.logger.error(f"Error fixing PR: {e}", exc_info=True)
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=pr_number,
                    title="",
                    repository=f"{owner}/{repo}",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=str(e),
                error=str(e),
            )

    async def _fix_pr_with_git(
        self,
        pr_info: PRInfo,
        clone_url: str,
        owner: str,
        repo: str,
        *,
        sync_strategy: str = "none",
        conflict_strategy: str = "fail",
        dry_run: bool = False,
    ) -> GitHubFixResult:
        """Fix PR using Git operations (clone, fix, amend, push).

        Args:
            pr_info: PR information
            clone_url: Repository clone URL
            owner: Repository owner
            repo: Repository name
            sync_strategy: How to sync with base branch: 'none', 'rebase', or 'merge'
            conflict_strategy: How to resolve conflicts: 'fail', 'ours', or 'theirs'
            dry_run: If True, don't push changes

        Returns:
            GitHubFixResult with operation details
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            self.logger.debug(f"Cloning {clone_url} to {repo_dir}")

            try:
                # Clone the repository
                auth_url = clone_url.replace(
                    "https://", f"https://x-access-token:{self.client.token}@"
                )
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        pr_info.head_ref,
                        auth_url,
                        str(repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Sync with base branch if requested
                if sync_strategy in ["rebase", "merge"]:
                    try:
                        await self._sync_with_base(
                            repo_dir,
                            pr_info.base_ref,
                            pr_info.head_ref,
                            sync_strategy,
                            conflict_strategy,
                        )
                    except subprocess.CalledProcessError as e:
                        return GitHubFixResult(
                            pr_info=pr_info,
                            success=False,
                            message=f"Failed to sync with base branch using {sync_strategy}: {e.stderr}",
                            error=str(e),
                        )

                # Find and fix markdown files
                scanner = MarkdownFileScanner(repo_dir)
                markdown_files = scanner.find_markdown_files()

                self.logger.debug(f"Found {len(markdown_files)} markdown files")

                files_modified = []
                tables_fixed = 0

                for md_file in markdown_files:
                    self.logger.debug(f"Processing {md_file}")

                    # Parse tables
                    parser = TableParser(md_file)
                    tables = parser.parse_file()

                    if not tables:
                        continue

                    # Check if any tables have issues
                    has_issues = False
                    for table in tables:
                        validator = TableValidator(table)
                        violations = validator.validate()
                        if violations:
                            has_issues = True
                            break

                    if not has_issues:
                        continue

                    # Fix the file
                    fixer = FileFixer(md_file, max_line_length=80)
                    fixes = fixer.fix_file(tables, dry_run=False)

                    if fixes:
                        files_modified.append(md_file)
                        tables_fixed += len(fixes)
                        self.logger.debug(
                            f"Fixed {len(fixes)} table(s) in {md_file.name}"
                        )

                # Handle no files modified or dry-run mode
                if not files_modified or dry_run:
                    if not files_modified:
                        message = "No markdown table issues found"
                        result_files: list[Path] = []
                    else:
                        file_names = [
                            str(f.relative_to(repo_dir)) for f in files_modified
                        ]
                        message = f"[DRY RUN] Would fix {tables_fixed} table(s) in {len(files_modified)} file(s): {', '.join(file_names)}"
                        result_files = files_modified
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message=message,
                        files_modified=result_files,
                    )

                # Configure git
                subprocess.run(
                    ["git", "config", "user.name", "markdown-table-fixer"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        "git",
                        "config",
                        "user.email",
                        "noreply@linuxfoundation.org",
                    ],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )

                # Stage the changes
                for file_path in files_modified:
                    rel_path = file_path.relative_to(repo_dir)
                    subprocess.run(
                        ["git", "add", str(rel_path)],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                    )

                # Check if there are actually changes to commit
                result = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    check=False,
                    cwd=repo_dir,
                    capture_output=True,
                )

                if result.returncode == 0:
                    # No changes
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message="Files were already properly formatted",
                        files_modified=[],
                    )

                # Amend the last commit
                self.logger.debug("Amending last commit with table fixes")
                subprocess.run(
                    ["git", "commit", "--amend", "--no-edit"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Force push to update the PR
                self.logger.debug(f"Force pushing to {pr_info.head_ref}")
                subprocess.run(
                    [
                        "git",
                        "push",
                        "--force-with-lease",
                        "origin",
                        pr_info.head_ref,
                    ],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Create a comment on the PR
                sync_msg = ""
                if sync_strategy == "rebase":
                    sync_msg = " and rebased onto the base branch"
                elif sync_strategy == "merge":
                    sync_msg = " and merged with the base branch"

                comment_body = (
                    f"🛠️ **Markdown Table Fixer**\n\n"
                    f"Fixed {tables_fixed} markdown table(s) in {len(files_modified)} file(s).\n\n"
                    f"The commit has been amended{sync_msg} with the formatting fixes.\n\n"
                    f"---\n"
                    f"*Automatically fixed by [markdown-table-fixer]"
                    f"(https://github.com/lfit/markdown-table-fixer)*"
                )

                with suppress(Exception):
                    await self.client.create_comment(
                        owner, repo, pr_info.number, comment_body
                    )

                return GitHubFixResult(
                    pr_info=pr_info,
                    success=True,
                    message=f"Fixed {tables_fixed} table(s) in {len(files_modified)} file(s)",
                    files_modified=files_modified,
                )

            except subprocess.CalledProcessError as e:
                self.logger.error(f"Git operation failed: {e.stderr}")
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=f"Git operation failed: {e.stderr}",
                    error=str(e),
                )
            except Exception as e:
                self.logger.error(f"Error during fix: {e}", exc_info=True)
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=str(e),
                    error=str(e),
                )

    async def _sync_with_base(
        self,
        repo_dir: Path,
        base_ref: str,
        head_ref: str,
        sync_strategy: str,
        conflict_strategy: str = "fail",
    ) -> None:
        """Sync PR branch with base branch using specified strategy.

        Args:
            repo_dir: Local repository directory
            base_ref: Base branch name (e.g., 'main')
            head_ref: PR branch name
            sync_strategy: 'rebase' or 'merge'
            conflict_strategy: How to resolve conflicts: 'fail', 'ours', or 'theirs'

        Raises:
            subprocess.CalledProcessError: If sync operation fails
        """
        # Fetch the base branch
        self.logger.info(f"Fetching origin/{base_ref}")
        subprocess.run(
            ["git", "fetch", "origin", base_ref],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        if sync_strategy == "rebase":
            self.logger.info(f"Rebasing {head_ref} onto origin/{base_ref}")
            try:
                rebase_cmd = ["git", "rebase", f"origin/{base_ref}"]
                if conflict_strategy == "ours":
                    rebase_cmd.extend(["-X", "ours"])
                elif conflict_strategy == "theirs":
                    rebase_cmd.extend(["-X", "theirs"])

                subprocess.run(
                    rebase_cmd,
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.logger.info("Rebase successful")
            except subprocess.CalledProcessError as e:
                if conflict_strategy == "fail":
                    # Abort rebase on failure
                    subprocess.run(
                        ["git", "rebase", "--abort"],
                        check=False,
                        cwd=repo_dir,
                        capture_output=True,
                    )
                    error_msg = f"Rebase failed: {e.stderr}"
                    self.logger.error(error_msg)
                    raise subprocess.CalledProcessError(
                        e.returncode, e.cmd, e.output, e.stderr
                    ) from e
                else:
                    self.logger.warning(
                        f"Rebase had conflicts, attempting to resolve with strategy '{conflict_strategy}'"
                    )

        elif sync_strategy == "merge":
            self.logger.info(f"Merging origin/{base_ref} into {head_ref}")
            try:
                merge_cmd = [
                    "git",
                    "merge",
                    f"origin/{base_ref}",
                    "-m",
                    f"Merge {base_ref} into {head_ref} for markdown table fixes",
                    "--no-edit",
                    "--allow-unrelated-histories",
                ]

                if conflict_strategy == "ours":
                    merge_cmd.extend(["-X", "ours"])
                elif conflict_strategy == "theirs":
                    merge_cmd.extend(["-X", "theirs"])

                subprocess.run(
                    merge_cmd,
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.logger.info("Merge successful")
            except subprocess.CalledProcessError as e:
                if conflict_strategy == "fail":
                    # Abort merge on failure
                    subprocess.run(
                        ["git", "merge", "--abort"],
                        check=False,
                        cwd=repo_dir,
                        capture_output=True,
                    )
                    error_msg = f"Merge failed: {e.stderr}"
                    self.logger.error(error_msg)
                    raise subprocess.CalledProcessError(
                        e.returncode, e.cmd, e.output, e.stderr
                    ) from e
                else:
                    self.logger.warning(
                        f"Merge had conflicts, attempting to resolve with strategy '{conflict_strategy}'"
                    )

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

        self.logger.debug(
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
