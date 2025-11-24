# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Custom exceptions for markdown table fixer."""

from __future__ import annotations


class MarkdownTableFixerError(Exception):
    """Base exception for markdown table fixer."""

    pass


class FileAccessError(MarkdownTableFixerError):
    """Error accessing or reading a file."""

    pass


class TableParseError(MarkdownTableFixerError):
    """Error parsing a markdown table."""

    pass


class TableValidationError(MarkdownTableFixerError):
    """Error validating table format."""

    pass


class GitHubAPIError(MarkdownTableFixerError):
    """Error communicating with GitHub API."""

    pass


class AuthenticationError(GitHubAPIError):
    """GitHub authentication failed."""

    pass


class RateLimitError(GitHubAPIError):
    """GitHub API rate limit exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: int | None = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            reset_time: Unix timestamp when rate limit resets
        """
        super().__init__(message)
        self.reset_time = reset_time


class NetworkError(MarkdownTableFixerError):
    """Network communication error."""

    pass


class GitOperationError(MarkdownTableFixerError):
    """Error performing git operation."""

    pass


class FixError(MarkdownTableFixerError):
    """Error applying table fix."""

    pass


class ConfigurationError(MarkdownTableFixerError):
    """Configuration error."""

    pass


class MarkdownLintError(MarkdownTableFixerError):
    """Error running markdownlint."""

    pass
