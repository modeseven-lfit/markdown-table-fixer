# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""GitHub API client for repository and PR operations."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .exceptions import FileAccessError


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            base_url: GitHub API base URL
        """
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON data

        Raises:
            FileAccessError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    **kwargs,
                )
                response.raise_for_status()
                result: dict[str, Any] | list[dict[str, Any]] = response.json()
                return result
            except httpx.HTTPStatusError as e:
                msg = f"GitHub API error: {e.response.status_code} - {e.response.text}"
                raise FileAccessError(msg) from e
            except httpx.RequestError as e:
                msg = f"GitHub API request failed: {e}"
                raise FileAccessError(msg) from e

    async def get_org_repos(
        self, org: str, per_page: int = 100
    ) -> AsyncIterator[dict[str, Any]]:
        """Get all repositories in an organization.

        Args:
            org: Organization name
            per_page: Results per page

        Yields:
            Repository data
        """
        page = 1
        while True:
            repos = await self._request(
                "GET",
                f"/orgs/{org}/repos",
                params={"per_page": per_page, "page": page, "type": "all"},
            )
            if not isinstance(repos, list) or not repos:
                break

            for repo in repos:
                yield repo

            if len(repos) < per_page:
                break

            page += 1

    async def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 100,
    ) -> AsyncIterator[dict[str, Any]]:
        """Get pull requests for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            per_page: Results per page

        Yields:
            Pull request data
        """
        page = 1
        while True:
            prs = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": per_page, "page": page},
            )
            if not isinstance(prs, list) or not prs:
                break

            for pr in prs:
                yield pr

            if len(prs) < per_page:
                break

            page += 1

    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Get files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of changed files
        """
        files = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
        )
        return files if isinstance(files, list) else []

    async def get_pr_checks(
        self, owner: str, repo: str, ref: str
    ) -> dict[str, Any]:
        """Get check runs for a PR ref.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git ref (branch/commit SHA)

        Returns:
            Check runs data
        """
        result = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits/{ref}/check-runs",
        )
        return result if isinstance(result, dict) else {}

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str:
        """Get file content from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git ref (branch/commit SHA)

        Returns:
            Decoded file content

        Raises:
            FileAccessError: If file cannot be retrieved
        """
        result = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response type for file content: {type(result)}"
            raise FileAccessError(msg)

        content_b64 = result.get("content", "")
        if not content_b64:
            return ""

        try:
            return base64.b64decode(content_b64).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            msg = f"Failed to decode file content: {e}"
            raise FileAccessError(msg) from e

    async def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str,
    ) -> dict[str, Any]:
        """Update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: New file content
            message: Commit message
            branch: Branch name
            sha: Current file SHA (for conflict detection)

        Returns:
            Commit data
        """
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        result = await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/contents/{path}",
            json={
                "message": message,
                "content": content_b64,
                "branch": branch,
                "sha": sha,
            },
        )
        return result if isinstance(result, dict) else {}

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current API rate limit status.

        Returns:
            Rate limit information
        """
        result = await self._request("GET", "/rate_limit")
        return result if isinstance(result, dict) else {}

    async def create_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        """Create a comment on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment body

        Returns:
            Comment data
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        return result if isinstance(result, dict) else {}
