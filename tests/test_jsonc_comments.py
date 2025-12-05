# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test JSONC comment removal functionality."""

from pathlib import Path

import pytest

from markdown_table_fixer.table_fixer import FileFixer


@pytest.fixture
def file_fixer(tmp_path: Path) -> FileFixer:
    """Create a FileFixer instance for testing."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")
    return FileFixer(test_file)


def test_remove_simple_line_comment(file_fixer: FileFixer) -> None:
    """Test removal of simple line comment."""
    content = '{"key": "value"} // This is a comment'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"key": "value"} '


def test_remove_comment_at_line_start(file_fixer: FileFixer) -> None:
    """Test removal of comment at start of line."""
    content = '// This is a comment\n{"key": "value"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '\n{"key": "value"}'


def test_preserve_url_in_string(file_fixer: FileFixer) -> None:
    """Test that URLs with // are preserved inside strings."""
    content = '{"url": "https://example.com"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"url": "https://example.com"}'


def test_preserve_comment_chars_in_string(file_fixer: FileFixer) -> None:
    """Test that // inside strings is preserved."""
    content = '{"comment": "This // is not a comment"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"comment": "This // is not a comment"}'


def test_remove_comment_after_string(file_fixer: FileFixer) -> None:
    """Test removing comment after a string value."""
    content = '{"url": "https://example.com"} // Real comment'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"url": "https://example.com"} '


def test_multiline_with_mixed_content(file_fixer: FileFixer) -> None:
    """Test multiline content with strings and comments."""
    content = """
{
  "url": "https://example.com", // This is a comment
  "path": "//some/path", // Another comment
  "key": "value"
}
"""
    result = file_fixer._remove_jsonc_comments(content)
    lines = result.split("\n")
    assert '"url": "https://example.com",' in lines[2]
    assert '"path": "//some/path",' in lines[3]
    assert '"key": "value"' in lines[4]
    # Comments should be removed
    assert "// This is a comment" not in result
    assert "// Another comment" not in result


def test_escaped_quote_in_string(file_fixer: FileFixer) -> None:
    """Test that escaped quotes are handled correctly."""
    content = r'{"text": "He said \"hello\" // not a comment"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert r'"He said \"hello\" // not a comment"' in result


def test_backslash_before_comment(file_fixer: FileFixer) -> None:
    """Test backslash followed by comment."""
    content = r'{"path": "C:\\path\\to\\file"} // Comment'
    result = file_fixer._remove_jsonc_comments(content)
    assert r'"path": "C:\\path\\to\\file"' in result
    assert "// Comment" not in result


def test_empty_string(file_fixer: FileFixer) -> None:
    """Test empty content."""
    content = ""
    result = file_fixer._remove_jsonc_comments(content)
    assert result == ""


def test_only_comment(file_fixer: FileFixer) -> None:
    """Test content with only a comment."""
    content = "// Just a comment"
    result = file_fixer._remove_jsonc_comments(content)
    assert result == ""


def test_multiple_comments_on_line(file_fixer: FileFixer) -> None:
    """Test multiple // sequences (first one wins)."""
    content = '{"key": "value"} // First // Second'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"key": "value"} '
    assert "// First" not in result
    assert "// Second" not in result


def test_comment_with_no_preceding_space(file_fixer: FileFixer) -> None:
    """Test comment immediately after code."""
    content = '{"key":"value"}//comment'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"key":"value"}'


def test_string_with_escaped_backslash_then_quote(
    file_fixer: FileFixer,
) -> None:
    """Test string ending with escaped backslash followed by closing quote."""
    content = r'{"path": "ends with \\"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert r'"path": "ends with \\"' in result


def test_real_world_jsonc_config(file_fixer: FileFixer) -> None:
    """Test with realistic JSONC config."""
    content = """
{
  // Enable all rules by default
  "default": true,

  // Line length
  "MD013": {
    "line_length": 120,  // Max line length
    "url": "https://github.com/DavidAnson/markdownlint"  // Docs
  },

  // Disable some rules
  "MD041": false  // First line in file should be a top level heading
}
"""
    result = file_fixer._remove_jsonc_comments(content)

    # Check that JSON structure is preserved
    assert '"default": true' in result
    assert '"MD013":' in result
    assert '"line_length": 120' in result
    assert '"url": "https://github.com/DavidAnson/markdownlint"' in result
    assert '"MD041": false' in result

    # Check that comments are removed
    assert "// Enable all rules" not in result
    assert "// Line length" not in result
    assert "// Max line length" not in result
    assert "// Docs" not in result
    assert "// First line" not in result


def test_single_slash_in_string(file_fixer: FileFixer) -> None:
    """Test that single slash in string is preserved."""
    content = '{"path": "/usr/local/bin"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"path": "/usr/local/bin"}'


def test_empty_string_value(file_fixer: FileFixer) -> None:
    """Test empty string values."""
    content = '{"empty": ""} // Comment'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"empty": ""} '


def test_string_with_only_slashes(file_fixer: FileFixer) -> None:
    """Test string containing only slashes."""
    content = '{"slashes": "//"}'
    result = file_fixer._remove_jsonc_comments(content)
    assert result == '{"slashes": "//"}'


def test_unclosed_string(file_fixer: FileFixer) -> None:
    """Test handling of unclosed string (malformed JSON)."""
    content = '{"unclosed": "value'
    result = file_fixer._remove_jsonc_comments(content)
    # Should still process it without crashing
    assert '"unclosed": "value' in result


def test_comment_inside_multiline_value(file_fixer: FileFixer) -> None:
    """Test comment detection with multiline structure.

    Note: Our line-by-line processing doesn't handle multiline strings
    (which are not valid in standard JSON anyway). This test verifies
    the actual behavior rather than ideal behavior.
    """
    content = """{"key": "line1
line2 // not a comment
line3"}"""
    result = file_fixer._remove_jsonc_comments(content)
    # Due to line-by-line processing, the // on line 2 is treated as a comment
    # This is acceptable since multiline strings aren't common in config files
    assert "// not a comment" not in result
    # But the structure should still be somewhat preserved
    assert '"key": "line1' in result
