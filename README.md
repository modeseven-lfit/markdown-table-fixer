<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 🛠️ Markdown Table Fixer

A modern Python tool for automatically fixing markdown table formatting
issues. Works as a standalone CLI tool, pre-commit hook, and can bulk-fix
tables across GitHub organizations.

## Features

- **Lint Mode**: Scan directories for markdown files with table formatting
  issues
- **GitHub Mode**: Automatically fix tables in blocked PRs across an entire
  GitHub organization
- **Pre-commit Integration**: Run as a pre-commit hook to enforce table
  formatting standards
- **Markdownlint Compatible**: Fixes issues detected by markdownlint's
  MD060 rule
- **Parallel Processing**: Efficiently processes repositories and PRs in
  parallel

## Installation

```bash
pip install markdown-table-fixer
```

Or with uv:

```bash
uv pip install markdown-table-fixer
```

## Usage

### Lint Mode

Scan the current directory for markdown table formatting issues:

```bash
markdown-table-fixer lint
```

Scan a specific path:

```bash
markdown-table-fixer lint /path/to/docs
```

Auto-fix issues found:

```bash
markdown-table-fixer lint --auto-fix
```

### GitHub Mode

The `github` command intelligently handles both individual pull requests and
entire organizations.

#### Fix a Specific Pull Request

Fix markdown tables in a specific pull request by providing the PR URL:

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 --token YOUR_GITHUB_TOKEN
```

With environment variable for token:

```bash
export GITHUB_TOKEN=your_token_here
markdown-table-fixer github https://github.com/owner/repo/pull/123
```

Dry run to preview changes without applying them:

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 --dry-run
```

#### Update Methods

The tool supports two methods for applying fixes:

**API Method (default)** - Uses GitHub API to create new commits:

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123
```

- Creates new commits via GitHub API
- Shows as "Verified" by GitHub
- No Git operations required
- Faster and simpler
- Does not support sync strategies (rebase/merge)

**Git Method** - Clones repo, amends commit, force-pushes:

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 \
  --update-method git
```

- Respects your local Git signing configuration
- Amends the existing commit (preserves commit history)
- Requires Git operations (clone, amend, push)
- Use when you need to amend commits or use sync strategies

#### Fix PRs Across an Organization

Scan and fix tables in PRs across an entire GitHub organization:

```bash
markdown-table-fixer github ORG_NAME --token YOUR_GITHUB_TOKEN
```

Or using an organization URL:

```bash
markdown-table-fixer github https://github.com/ORG_NAME/
```

You can also provide the GitHub token via the `GITHUB_TOKEN` environment
variable:

```bash
export GITHUB_TOKEN=your_token_here
markdown-table-fixer github ORG_NAME
```

### Pre-commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/lfit/markdown-table-fixer
    rev: v1.0.0
    hooks:
      - id: markdown-table-fixer
        # Automatically fixes issues
```

Or use the check variant for validation without auto-fixing:

```yaml
repos:
  - repo: https://github.com/lfit/markdown-table-fixer
    rev: v1.0.0
    hooks:
      - id: markdown-table-fixer-check
        # Validates, doesn't fix
```

Available hooks:

- `markdown-table-fixer`: Automatically fixes table formatting issues
- `markdown-table-fixer-check`: Checks for issues without fixing (CI mode)

## Table Formatting Rules

The tool enforces the following formatting standards:

1. **Alignment**: All pipe symbols (`|`) must be vertically aligned
2. **Spacing**: Cell content must have at least one space on each side
3. **Consistency**: All rows in a table must follow the same formatting
   style

### Correct Format

<!-- markdownlint-disable MD013 -->

| Name    | Required | Description  |
| ------- | -------- | ------------ |
| input   | False    | Action input |
| verbose | True     | Enable logs  |

<!-- markdownlint-enable MD013 -->

### Incorrect Format (Fixed Automatically)

<!-- markdownlint-disable MD013 -->

```markdown
| Name    | Required | Description  |
| ------- | -------- | ------------ |
| input   | False    | Action input |
| verbose | True     | Enable logs  |
```

<!-- markdownlint-enable MD013 -->

## Options

### Lint Command

<!-- markdownlint-disable MD013 -->

| Flag         | Short | Default | Description                     |
| ------------ | ----- | ------- | ------------------------------- |
| `--auto-fix` |       | `false` | Automatically fix issues found  |
| `--format`   |       | `text`  | Output format: text, json       |
| `--quiet`    | `-q`  | `false` | Suppress output except errors   |
| `--check`    |       | `false` | Exit with error if issues found |

<!-- markdownlint-enable MD013 -->

### GitHub Command

<!-- markdownlint-disable MD013 -->

| Flag               | Short | Default | Description                         |
| ------------------ | ----- | ------- | ----------------------------------- |
| `--token`          | `-t`  | `None`  | GitHub token (or use $GITHUB_TOKEN) |
| `--threads`        |       | `auto`  | Number of parallel threads          |
| `--dry-run`        |       | `false` | Preview changes without applying    |
| `--format`         |       | `table` | Output format: table, json          |
| `--include-drafts` |       | `false` | Include draft PRs                   |

<!-- markdownlint-enable MD013 -->

## Development

### Setup

```bash
git clone https://github.com/lfit/markdown-table-fixer.git
cd markdown-table-fixer
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Running Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## License

Apache-2.0

## Contributing

Contributions are welcome! Please see our contributing guidelines for more
information.
