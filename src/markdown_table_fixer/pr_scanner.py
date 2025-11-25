# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Scanner for identifying pull requests with markdown table issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .github_client import GitHubClient


class PRScanner:
    """Scanner for finding PRs with markdown table formatting issues."""

    def __init__(self, client: GitHubClient):
        """Initialize PR scanner.

        Args:
            client: GitHub API client
        """
        self.client = client

    async def scan_organization(
        self,
        org: str,
        *,
        include_drafts: bool = False,
    ) -> AsyncIterator[tuple[str, str, dict[str, Any]]]:
        """Scan all repositories in an organization for PRs with issues.

        Args:
            org: Organization name
            include_drafts: Whether to include draft PRs

        Yields:
            Tuple of (owner, repo, pr_data) for each PR with potential issues
        """
        async for repo in self.client.get_org_repos(org):
            repo_name = repo.get("name", "")
            owner = repo.get("owner", {}).get("login", org)

            if not repo_name:
                continue

            # Skip archived repositories
            if repo.get("archived", False):
                continue

            async for pr in self.client.get_pull_requests(owner, repo_name):
                # Skip draft PRs unless explicitly included
                if pr.get("draft", False) and not include_drafts:
                    continue

                # Check if PR has markdown files that might need fixing
                if await self._pr_has_markdown_files(owner, repo_name, pr):
                    yield owner, repo_name, pr

    async def _pr_has_markdown_files(
        self, owner: str, repo: str, pr: dict[str, Any]
    ) -> bool:
        """Check if a PR contains markdown files.

        Args:
            owner: Repository owner
            repo: Repository name
            pr: Pull request data

        Returns:
            True if PR contains markdown files
        """
        pr_number = pr.get("number")
        if not pr_number:
            return False

        try:
            files = await self.client.get_pr_files(owner, repo, pr_number)
            return any(
                f.get("filename", "").endswith(".md")
                for f in files
                if f.get("status") != "removed"
            )
        except Exception:
            # If we can't get files, assume it might have markdown
            return True

    async def is_pr_blocked(
        self, owner: str, repo: str, pr: dict[str, Any]
    ) -> bool:
        """Check if a PR is blocked by failing checks.

        Args:
            owner: Repository owner
            repo: Repository name
            pr: Pull request data

        Returns:
            True if PR has failing checks
        """
        head_sha = pr.get("head", {}).get("sha")
        if not head_sha:
            return False

        try:
            checks = await self.client.get_pr_checks(owner, repo, head_sha)
            check_runs = checks.get("check_runs", [])

            # Look for failing checks related to markdown or linting
            for check in check_runs:
                conclusion = check.get("conclusion", "")
                status = check.get("status", "")
                name = check.get("name", "").lower()

                # Check is completed and failed with markdown/linting keywords
                if (
                    status == "completed"
                    and conclusion in ("failure", "action_required")
                    and any(
                        keyword in name
                        for keyword in [
                            "markdown",
                            "lint",
                            "pre-commit",
                            "table",
                            "format",
                        ]
                    )
                ):
                    return True

            return False
        except Exception:
            # If we can't get checks, assume not blocked
            return False

    async def get_markdown_files_from_pr(
        self, owner: str, repo: str, pr: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get all markdown files from a PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr: Pull request data

        Returns:
            List of markdown file data
        """
        pr_number = pr.get("number")
        if not pr_number:
            return []

        try:
            files = await self.client.get_pr_files(owner, repo, pr_number)
            return [
                f
                for f in files
                if f.get("filename", "").endswith(".md")
                and f.get("status") != "removed"
            ]
        except Exception:
            return []
