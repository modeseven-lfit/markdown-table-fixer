# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Tests for git_config module."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from markdown_table_fixer.git_config import (
    GitConfigMode,
    _get_global_git_config,
    _set_repo_git_config,
    configure_git_identity,
    get_signing_info,
)


class TestGetGlobalGitConfig:
    """Tests for _get_global_git_config function."""

    def test_get_existing_config(self) -> None:
        """Test getting an existing git config value."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="John Doe\n")
            result = _get_global_git_config("user.name")
            assert result == "John Doe"
            mock_run.assert_called_once_with(
                ["git", "config", "--global", "user.name"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_get_nonexistent_config(self) -> None:
        """Test getting a non-existent git config value."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = _get_global_git_config("user.nonexistent")
            assert result is None

    def test_get_empty_config(self) -> None:
        """Test getting an empty git config value."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = _get_global_git_config("user.name")
            assert result is None


class TestSetRepoGitConfig:
    """Tests for _set_repo_git_config function."""

    def test_set_config_success(self) -> None:
        """Test successfully setting a git config value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = _set_repo_git_config(repo_dir, "user.name", "Test")
                assert result is True

    def test_set_config_failure(self) -> None:
        """Test handling failure when setting git config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "git")
                result = _set_repo_git_config(repo_dir, "user.name", "Test")
                assert result is False


class TestConfigureGitIdentity:
    """Tests for configure_git_identity function."""

    def test_bot_identity_mode(self) -> None:
        """Test BOT_IDENTITY mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                config = configure_git_identity(
                    repo_dir,
                    mode=GitConfigMode.BOT_IDENTITY,
                    bot_name="test-bot",
                    bot_email="bot@example.com",
                )

                assert config["user.name"] == "test-bot"
                assert config["user.email"] == "bot@example.com"
                assert config["mode"] == "bot_identity"
                assert "commit.gpgsign" not in config

    def test_user_inherit_mode_no_signing(self) -> None:
        """Test USER_INHERIT mode when user has no signing enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if cmd == ["git", "config", "--global", "user.name"]:
                    return MagicMock(returncode=0, stdout="Jane Doe\n")
                if cmd == ["git", "config", "--global", "user.email"]:
                    return MagicMock(returncode=0, stdout="jane@example.com\n")
                if cmd == ["git", "config", "--global", "commit.gpgsign"]:
                    return MagicMock(returncode=1, stdout="")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                config = configure_git_identity(
                    repo_dir, mode=GitConfigMode.USER_INHERIT
                )

                assert config["user.name"] == "Jane Doe"
                assert config["user.email"] == "jane@example.com"
                assert config["mode"] == "user_inherit"
                assert "commit.gpgsign" not in config

    def test_user_inherit_mode_with_gpg_signing(self) -> None:
        """Test USER_INHERIT mode with GPG signing enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001, PLR0911
                if cmd == ["git", "config", "--global", "user.name"]:
                    return MagicMock(returncode=0, stdout="Jane Doe\n")
                if cmd == ["git", "config", "--global", "user.email"]:
                    return MagicMock(returncode=0, stdout="jane@example.com\n")
                if cmd == ["git", "config", "--global", "commit.gpgsign"]:
                    return MagicMock(returncode=0, stdout="true\n")
                if cmd == ["git", "config", "--global", "gpg.format"]:
                    return MagicMock(returncode=0, stdout="openpgp\n")
                if cmd == ["git", "config", "--global", "user.signingkey"]:
                    return MagicMock(returncode=0, stdout="ABCD1234\n")
                if cmd == ["git", "config", "--global", "gpg.program"]:
                    return MagicMock(returncode=0, stdout="/usr/bin/gpg2\n")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                config = configure_git_identity(
                    repo_dir, mode=GitConfigMode.USER_INHERIT
                )

                assert config["user.name"] == "Jane Doe"
                assert config["user.email"] == "jane@example.com"
                assert config["commit.gpgsign"] == "true"
                assert config["gpg.format"] == "openpgp"
                assert config["user.signingkey"] == "ABCD1234"
                assert config["gpg.program"] == "/usr/bin/gpg2"
                assert config["mode"] == "user_inherit"

    def test_user_inherit_mode_with_ssh_signing(self) -> None:
        """Test USER_INHERIT mode with SSH signing enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001, PLR0911
                if cmd == ["git", "config", "--global", "user.name"]:
                    return MagicMock(returncode=0, stdout="Jane Doe\n")
                if cmd == ["git", "config", "--global", "user.email"]:
                    return MagicMock(returncode=0, stdout="jane@example.com\n")
                if cmd == ["git", "config", "--global", "commit.gpgsign"]:
                    return MagicMock(returncode=0, stdout="true\n")
                if cmd == ["git", "config", "--global", "gpg.format"]:
                    return MagicMock(returncode=0, stdout="ssh\n")
                if cmd == ["git", "config", "--global", "user.signingkey"]:
                    return MagicMock(
                        returncode=0, stdout="~/.ssh/id_ed25519.pub\n"
                    )
                if cmd == [
                    "git",
                    "config",
                    "--global",
                    "gpg.ssh.allowedSignersFile",
                ]:
                    return MagicMock(
                        returncode=0, stdout="~/.ssh/allowed_signers\n"
                    )
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                config = configure_git_identity(
                    repo_dir, mode=GitConfigMode.USER_INHERIT
                )

                assert config["user.name"] == "Jane Doe"
                assert config["user.email"] == "jane@example.com"
                assert config["commit.gpgsign"] == "true"
                assert config["gpg.format"] == "ssh"
                assert config["user.signingkey"] == "~/.ssh/id_ed25519.pub"
                assert (
                    config["gpg.ssh.allowedSignersFile"]
                    == "~/.ssh/allowed_signers"
                )
                assert config["mode"] == "user_inherit"

    def test_user_no_sign_mode(self) -> None:
        """Test USER_NO_SIGN mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if cmd == ["git", "config", "--global", "user.name"]:
                    return MagicMock(returncode=0, stdout="Jane Doe\n")
                if cmd == ["git", "config", "--global", "user.email"]:
                    return MagicMock(returncode=0, stdout="jane@example.com\n")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                config = configure_git_identity(
                    repo_dir, mode=GitConfigMode.USER_NO_SIGN
                )

                assert config["user.name"] == "Jane Doe"
                assert config["user.email"] == "jane@example.com"
                assert config["commit.gpgsign"] == "false"
                assert config["mode"] == "user_no_sign"

    def test_user_mode_fallback_to_bot(self) -> None:
        """Test fallback to bot identity when user config not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if "user.name" in cmd or "user.email" in cmd:
                    return MagicMock(returncode=1, stdout="")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                config = configure_git_identity(
                    repo_dir,
                    mode=GitConfigMode.USER_INHERIT,
                    bot_name="fallback-bot",
                    bot_email="fallback@example.com",
                )

                assert config["user.name"] == "fallback-bot"
                assert config["user.email"] == "fallback@example.com"
                assert config["mode"] == "bot_identity_fallback"

    def test_invalid_mode(self) -> None:
        """Test that invalid mode raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)
            with pytest.raises(ValueError, match="Invalid mode"):
                configure_git_identity(repo_dir, mode="invalid_mode")


class TestGetSigningInfo:
    """Tests for get_signing_info function."""

    def test_signing_enabled_with_ssh(self) -> None:
        """Test getting signing info when SSH signing is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if "commit.gpgsign" in cmd:
                    return MagicMock(returncode=0, stdout="true\n")
                if "gpg.format" in cmd:
                    return MagicMock(returncode=0, stdout="ssh\n")
                if "user.signingkey" in cmd:
                    return MagicMock(returncode=0, stdout="~/.ssh/key.pub\n")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                info = get_signing_info(repo_dir)

                assert info["signing_enabled"] is True
                assert info["format"] == "ssh"
                assert info["signing_key"] == "~/.ssh/key.pub"

    def test_signing_disabled(self) -> None:
        """Test getting signing info when signing is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if "commit.gpgsign" in cmd:
                    return MagicMock(returncode=0, stdout="false\n")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                info = get_signing_info(repo_dir)

                assert info["signing_enabled"] is False
                assert "format" not in info
                assert "signing_key" not in info

    def test_signing_info_with_default_format(self) -> None:
        """Test that default format is openpgp when not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir)

            def mock_git_config(cmd, **kwargs):  # noqa: ARG001
                if "commit.gpgsign" in cmd:
                    return MagicMock(returncode=0, stdout="true\n")
                if "gpg.format" in cmd:
                    return MagicMock(returncode=0, stdout="")
                return MagicMock(returncode=0)

            with patch("subprocess.run", side_effect=mock_git_config):
                info = get_signing_info(repo_dir)

                assert info["signing_enabled"] is True
                assert info["format"] == "openpgp"
