# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Markdown table formatter and linter with GitHub integration."""

from __future__ import annotations

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

__all__ = ["__version__"]
