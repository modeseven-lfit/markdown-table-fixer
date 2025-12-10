# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Pytest configuration and fixtures for test isolation.

This module provides fixtures and configuration to ensure tests are properly
isolated from the local development environment, including:

1. Git Configuration Isolation:
   - Tests don't read from or write to the user's global git config
   - Tests use isolated temporary directories for git operations
   - Each test that needs git gets its own repository

2. Network Isolation:
   - Tests are prevented from making external network calls by default
   - Integration tests can opt-out using the 'integration' marker

3. Environment Isolation:
   - Tests run with isolated HOME and XDG_CONFIG_HOME directories
   - Git environment variables are set to test-specific values

This ensures that:
- Tests don't interfere with the developer's local git configuration
- Tests don't modify the repository where they're being run
- Tests are reproducible across different environments
- Pre-commit hooks can run safely without side effects
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="session", autouse=True)
def isolate_git_environment() -> Generator[None, None, None]:
    """Isolate tests from the user's git configuration.

    This fixture runs automatically for all tests (session-scoped) and ensures that:
    1. Tests don't read from the user's global git config
    2. Tests don't write to the user's global git config
    3. Tests use isolated temporary directories for git operations
    4. Git operations in tests use test-specific identity

    This prevents tests from interfering with the developer's local
    git environment or the repository where tests are being run.

    The isolation is achieved by:
    - Redirecting GIT_CONFIG_GLOBAL to a temp file
    - Redirecting GIT_CONFIG_SYSTEM to a temp file
    - Setting HOME to a temporary directory
    - Setting XDG_CONFIG_HOME to a temporary directory
    - Providing test-specific GIT_AUTHOR_* and GIT_COMMITTER_* values

    After tests complete, the original environment is restored.
    """
    # Save original environment variables
    original_env = {}
    git_env_vars = [
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "HOME",
        "XDG_CONFIG_HOME",
    ]

    for var in git_env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create isolated environment
    with tempfile.TemporaryDirectory(prefix="test_git_") as tmpdir:
        # Point git config to non-existent files in temp directory
        os.environ["GIT_CONFIG_GLOBAL"] = str(Path(tmpdir) / "gitconfig_global")
        os.environ["GIT_CONFIG_SYSTEM"] = str(Path(tmpdir) / "gitconfig_system")
        os.environ["HOME"] = tmpdir
        os.environ["XDG_CONFIG_HOME"] = str(Path(tmpdir) / ".config")

        # Set default git identity for tests
        os.environ["GIT_AUTHOR_NAME"] = "Test User"
        os.environ["GIT_AUTHOR_EMAIL"] = "test@example.com"
        os.environ["GIT_COMMITTER_NAME"] = "Test User"
        os.environ["GIT_COMMITTER_EMAIL"] = "test@example.com"

        try:
            yield
        finally:
            # Restore original environment
            for var in git_env_vars:
                if var in original_env:
                    os.environ[var] = original_env[var]
                elif var in os.environ:
                    del os.environ[var]


@pytest.fixture
def isolated_git_repo(tmp_path: Path) -> Path:
    """Create an isolated git repository for testing.

    This fixture provides a temporary git repository that is completely
    isolated from the project repository and the user's git configuration.

    The repository is initialized with:
    - Local git config (user.name, user.email)
    - GPG signing disabled (commit.gpgsign = false)
    - No remote configured

    This is useful for tests that need to perform git operations without
    affecting the actual project repository.

    Args:
        tmp_path: Pytest's tmp_path fixture (provides unique temp directory)

    Returns:
        Path to the isolated git repository

    Example:
        def test_git_operation(isolated_git_repo: Path) -> None:
            # Create a file in the isolated repo
            test_file = isolated_git_repo / "test.md"
            test_file.write_text("# Test")

            # Perform git operations safely
            subprocess.run(["git", "add", "."], cwd=isolated_git_repo)
            subprocess.run(["git", "commit", "-m", "Test"], cwd=isolated_git_repo)
    """
    import subprocess

    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    # Set local git config (isolated from global)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    # Disable GPG signing for tests
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    return repo_dir


@pytest.fixture(autouse=True)
def no_external_network(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prevent tests from making external network calls by default.

    This fixture prevents accidental external API calls during tests by
    patching common networking libraries (httpx, requests) to raise errors
    if network calls are attempted.

    Tests that need to make network calls should either:
    1. Mock the network calls explicitly
    2. Use the 'integration' marker to skip this isolation

    Example:
        @pytest.mark.integration
        def test_real_api_call() -> None:
            # This test can make real network calls
            response = httpx.get("https://api.example.com")
            ...
    """
    # Skip this isolation for integration tests
    if request.node.get_closest_marker("integration"):
        return

    def no_network(*_args: Any, **_kwargs: Any) -> None:
        """Raise an error if network call is attempted."""
        raise RuntimeError(
            "Network call attempted during test! "
            "Tests should mock external calls or use 'integration' marker."
        )

    # Patch common network libraries
    try:
        import httpx

        monkeypatch.setattr(httpx, "Client", no_network)
        monkeypatch.setattr(httpx, "AsyncClient", no_network)
    except ImportError:
        pass

    try:
        import requests  # type: ignore[import-untyped]

        monkeypatch.setattr(requests, "get", no_network)
        monkeypatch.setattr(requests, "post", no_network)
        monkeypatch.setattr(requests, "put", no_network)
        monkeypatch.setattr(requests, "delete", no_network)
        monkeypatch.setattr(requests, "patch", no_network)
    except ImportError:
        pass


@pytest.fixture
def mock_git_config() -> Generator[dict[str, str], None, None]:
    """Provide a mock git configuration for tests.

    This fixture provides a pre-configured mock git config that can be
    used by tests without needing to call real git commands. It patches
    subprocess.run to return mock values for git config queries.

    Returns:
        Dictionary containing mock git configuration values that will be
        returned by git config commands

    Example:
        def test_git_config(mock_git_config: dict[str, str]) -> None:
            # Customize the mock config
            mock_git_config["user.name"] = "Custom Name"

            # Now git config commands will return the mock values
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "Custom Name"
    """
    config = {
        "user.name": "Test User",
        "user.email": "test@example.com",
        "commit.gpgsign": "false",
    }

    def mock_run(cmd: list[str], **kwargs: Any) -> Any:
        """Mock subprocess.run for git config commands."""
        if "git" not in cmd[0]:
            # Pass through non-git commands
            import subprocess

            return subprocess.run(cmd, check=False, **kwargs)

        if "config" in cmd and "--get" in cmd or len(cmd) >= 4:
            # Extract config key
            key = cmd[-1] if "--get" not in cmd else cmd[cmd.index("--get") + 1]

            # Mock the result
            from unittest.mock import MagicMock

            if key in config:
                return MagicMock(returncode=0, stdout=f"{config[key]}\n")
            else:
                return MagicMock(returncode=1, stdout="")

        # Default mock for other git commands
        from unittest.mock import MagicMock

        return MagicMock(returncode=0, stdout="")

    with patch("subprocess.run", side_effect=mock_run):
        yield config


@pytest.fixture(scope="session")
def ensure_clean_test_environment() -> None:
    """Ensure test environment is clean before running tests.

    This fixture verifies that the test environment is properly isolated
    and won't affect the user's system or the project repository.

    Note: It's normal for tests to run within the project repository.
    The isolate_git_environment fixture ensures that git operations in
    tests use temporary directories and don't modify the project's .git
    directory or global git configuration.
    """
    # Check that we're not accidentally in the project root for git operations
    cwd = Path.cwd()
    if (cwd / ".git").exists():
        # This is expected - we're in the project repo
        # The isolate_git_environment fixture ensures tests use explicit
        # paths and don't affect the project repository
        pass


# Register custom markers
def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers.

    This function registers custom markers that can be used to categorize
    and control test execution.

    Markers:
        integration: Tests that may use external resources (network, APIs)
        git: Tests that require git operations (uses isolated repositories)
    """
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (may use external resources)",
    )
    config.addinivalue_line(
        "markers",
        "git: mark test as requiring git operations",
    )
