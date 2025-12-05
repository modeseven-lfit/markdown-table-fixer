# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test MD013 config checking functionality."""

from pathlib import Path

import pytest

from markdown_table_fixer.table_fixer import FileFixer


@pytest.fixture
def test_file(tmp_path: Path) -> Path:
    """Create a test markdown file."""
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")
    return test_file


def test_md013_enabled_by_default(tmp_path: Path, test_file: Path) -> None:  # noqa: ARG001
    """Test that MD013 is enabled when no config file exists."""
    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_disabled_in_json_config(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 disabled in JSON config."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_enabled_in_json_config(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 explicitly enabled in JSON config."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": true}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_not_specified_in_json(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 not specified in JSON config (should default to enabled)."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD001": true}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_disabled_in_jsonc_config(
    tmp_path: Path, test_file: Path
) -> None:
    """Test MD013 disabled in JSONC config with comments."""
    config_file = tmp_path / ".markdownlint.jsonc"
    config_file.write_text("""
{
  // This is a comment
  "MD013": false,  // Disable line length check
  "MD001": true
}
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_enabled_in_jsonc_with_inline_comments(
    tmp_path: Path, test_file: Path
) -> None:
    """Test JSONC config with inline comments."""
    config_file = tmp_path / ".markdownlint.jsonc"
    config_file.write_text("""
{
  "MD013": true,  // Enable line length check
  "MD001": false  // Some other rule
}
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_disabled_in_yaml_config(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 disabled in YAML config."""
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("""
MD013: false
MD001: true
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_enabled_in_yml_config(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 enabled in .yml config."""
    config_file = tmp_path / ".markdownlint.yml"
    config_file.write_text("""
MD013: true
MD001: false
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_not_specified_in_yaml(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 not specified in YAML config (should default to enabled)."""
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("""
MD001: true
MD002: false
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is True


def test_md013_disabled_in_markdownlintrc(
    tmp_path: Path, test_file: Path
) -> None:
    """Test MD013 disabled in .markdownlintrc file."""
    config_file = tmp_path / ".markdownlintrc"
    config_file.write_text('{"MD013": false}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_with_object_value(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 with object configuration (should be treated as enabled)."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": {"line_length": 120}}')

    fixer = FileFixer(test_file)
    # Non-false values are treated as enabled
    assert fixer._md013_enabled is True


def test_md013_with_malformed_json(tmp_path: Path, test_file: Path) -> None:
    """Test that malformed JSON falls back to enabled."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false invalid json}')

    fixer = FileFixer(test_file)
    # Should fall back to default (enabled)
    assert fixer._md013_enabled is True


def test_md013_with_malformed_yaml(tmp_path: Path, test_file: Path) -> None:
    """Test that malformed YAML falls back to enabled."""
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("""
MD013: false
  invalid: yaml: structure:
""")

    fixer = FileFixer(test_file)
    # Should fall back to default (enabled)
    assert fixer._md013_enabled is True


def test_md013_config_in_parent_directory(tmp_path: Path) -> None:
    """Test finding config in parent directory."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.md"
    test_file.write_text("# Test\n")

    # Config in parent directory
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_config_multiple_levels_up(tmp_path: Path) -> None:
    """Test finding config multiple directory levels up."""
    subdir1 = tmp_path / "level1"
    subdir2 = subdir1 / "level2"
    subdir3 = subdir2 / "level3"
    subdir3.mkdir(parents=True)
    test_file = subdir3 / "test.md"
    test_file.write_text("# Test\n")

    # Config at root level
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false}')

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_uses_closest_config(tmp_path: Path) -> None:
    """Test that closest config file takes precedence."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.md"
    test_file.write_text("# Test\n")

    # Parent config
    parent_config = tmp_path / ".markdownlint.json"
    parent_config.write_text('{"MD013": false}')

    # Closer config
    local_config = subdir / ".markdownlint.json"
    local_config.write_text('{"MD013": true}')

    fixer = FileFixer(test_file)
    # Should use the closer config
    assert fixer._md013_enabled is True


def test_md013_prefers_json_over_yaml_in_same_dir(
    tmp_path: Path, test_file: Path
) -> None:
    """Test precedence when multiple config files exist."""
    # Create both JSON and YAML configs
    json_config = tmp_path / ".markdownlint.json"
    json_config.write_text('{"MD013": false}')

    yaml_config = tmp_path / ".markdownlint.yaml"
    yaml_config.write_text("MD013: true")

    fixer = FileFixer(test_file)
    # JSON is checked first in the list
    assert fixer._md013_enabled is False


def test_md013_with_empty_json_config(tmp_path: Path, test_file: Path) -> None:
    """Test empty JSON config file."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text("{}")

    fixer = FileFixer(test_file)
    # Empty config should default to enabled
    assert fixer._md013_enabled is True


def test_md013_with_empty_yaml_config(tmp_path: Path, test_file: Path) -> None:
    """Test empty YAML config file."""
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("")

    fixer = FileFixer(test_file)
    # Empty config should default to enabled
    assert fixer._md013_enabled is True


def test_md013_with_null_value_in_json(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 with null value."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": null}')

    fixer = FileFixer(test_file)
    # null is not false, so should be enabled
    assert fixer._md013_enabled is True


def test_md013_with_zero_value(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 with numeric zero value."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": 0}')

    fixer = FileFixer(test_file)
    # 0 is not false, so should be enabled
    assert fixer._md013_enabled is True


def test_md013_with_string_false(tmp_path: Path, test_file: Path) -> None:
    """Test MD013 with string 'false' value."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": "false"}')

    fixer = FileFixer(test_file)
    # String "false" is not boolean false, so should be enabled
    assert fixer._md013_enabled is True


def test_md013_stops_at_root(tmp_path: Path) -> None:
    """Test that search stops at filesystem root."""
    # This test verifies the code doesn't crash when reaching root
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\n")

    fixer = FileFixer(test_file)
    # Should not crash and default to enabled
    assert fixer._md013_enabled is True


def test_md013_with_unreadable_config(tmp_path: Path, test_file: Path) -> None:
    """Test handling of unreadable config file."""
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false}')

    # Make file unreadable (Unix-like systems only)
    try:
        config_file.chmod(0o000)
        fixer = FileFixer(test_file)
        # Should fall back to enabled if can't read
        assert fixer._md013_enabled is True
    finally:
        # Restore permissions for cleanup
        config_file.chmod(0o644)


def test_md013_with_jsonc_multiline_comments(
    tmp_path: Path, test_file: Path
) -> None:
    """Test JSONC with comments on multiple lines."""
    config_file = tmp_path / ".markdownlint.jsonc"
    config_file.write_text("""
{
  // Comment line 1
  // Comment line 2
  "MD013": false,
  // Another comment
  "MD001": true
}
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_with_complex_yaml(tmp_path: Path, test_file: Path) -> None:
    """Test complex YAML config structure."""
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("""
# Comment in YAML
MD013: false
MD001:
  enabled: true
  option: value
MD002: true
""")

    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_config_search_limit(tmp_path: Path) -> None:
    """Test that config search stops after 5 levels."""
    # Create deeply nested structure (more than 5 levels)
    current = tmp_path
    for i in range(7):
        current = current / f"level{i}"
        current.mkdir()

    test_file = current / "test.md"
    test_file.write_text("# Test\n")

    # Config at the root (7 levels up)
    config_file = tmp_path / ".markdownlint.json"
    config_file.write_text('{"MD013": false}')

    fixer = FileFixer(test_file)
    # Should NOT find the config (too far up) and default to enabled
    assert fixer._md013_enabled is True


def test_md013_with_yaml_boolean_variations(
    tmp_path: Path, test_file: Path
) -> None:
    """Test various YAML boolean representations."""
    # Test with lowercase 'false'
    config_file = tmp_path / ".markdownlint.yaml"
    config_file.write_text("MD013: false")
    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False

    # Test with 'False' (capital F)
    config_file.write_text("MD013: False")
    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False

    # Test with 'no'
    config_file.write_text("MD013: no")
    fixer = FileFixer(test_file)
    assert fixer._md013_enabled is False


def test_md013_with_bom_in_json(tmp_path: Path, test_file: Path) -> None:
    """Test JSON file with BOM (Byte Order Mark).

    Note: Python's json.loads() doesn't handle UTF-8 BOM automatically
    and raises JSONDecodeError. This is expected behavior and the code
    will fall back to enabled (default) when JSON parsing fails.
    """
    config_file = tmp_path / ".markdownlint.json"
    # Write with UTF-8 BOM
    config_file.write_text('\ufeff{"MD013": false}', encoding="utf-8")

    fixer = FileFixer(test_file)
    # JSON parsing will fail due to BOM, falls back to default (enabled)
    assert fixer._md013_enabled is True
