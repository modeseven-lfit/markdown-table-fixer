<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# GitHub PR Fixing

The `markdown-table-fixer` can automatically fix markdown tables in GitHub
Pull Requests by cloning the PR branch, applying fixes, amending the commit,
and force-pushing the changes. It can also scan entire GitHub organizations
to find and fix PRs blocked by markdown/lint failures.

## Usage

### Organization Scanning

Scan an entire GitHub organization for PRs blocked by markdown/lint check
failures:

```bash
# Scan organization and fix all blocked PRs
markdown-table-fixer github lfreleng-actions

# Preview changes without applying them
markdown-table-fixer github lfreleng-actions --dry-run

# Scan and include draft PRs
markdown-table-fixer github lfreleng-actions --include-drafts

# Debug mode: process the first PR found
markdown-table-fixer github lfreleng-actions --debug-org --dry-run
```

**How it works:**

1. Scans all repositories in the organization using efficient GraphQL queries
2. Identifies PRs with failing markdown/lint checks
3. Processes each blocked PR to fix table formatting issues
4. Shows real-time progress with repository and PR counts
5. Displays summary of fixed PRs with URLs

**Example output:**

```shell
🔍 Scanning organization: lfreleng-actions
🔍 Checking lfreleng-actions (78/78 repos, 100%) | 84 PRs analyzed | 26 unmergeable
⏱️  Elapsed: 10s
📊 Found 26 blocked PRs with potential markdown issues

🔄 Processing: lfreleng-actions/gerrit-change-info#55
✅ Fixed 2 table(s) in 1 file(s)

✅ Fixed 5 PR(s):
   • https://github.com/lfreleng-actions/repo1/pull/123
   • https://github.com/lfreleng-actions/repo2/pull/456
```

### Single PR Fixing

Fix a specific PR by providing its URL:

```bash
# Fix a specific PR (no sync with base branch)
markdown-table-fixer github https://github.com/owner/repo/pull/123

# Preview changes without pushing
markdown-table-fixer github https://github.com/owner/repo/pull/123 --dry-run
```

### Sync Strategies

When fixing tables in a PR, you can choose how to sync the PR branch with
the base branch (e.g., `main`):

#### 1. None (Default)

Fixes tables on the PR branch as-is without syncing with the base branch.

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 --sync-strategy=none
```

**Use when:**

- The PR is up-to-date with base branch
- You prefer to keep the PR's commit history unchanged
- The PR doesn't have conflicts

**Pros:**

- Fast - no extra git operations
- Preserves PR commit structure
- No risk of merge/rebase failures

**Cons:**

- May result in conflicts if base branch has diverged
- Doesn't ensure PR is mergeable

#### 2. Rebase

Rebases the PR branch onto the latest base branch before applying fixes.

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 --sync-strategy=rebase
```

**Use when:**

- You want a clean, linear commit history
- The PR has a small number of commits and simple changes
- You prefer rebasing over merging

**Pros:**

- Clean, linear history
- No merge commits
- Ensures PR is up-to-date with base

**Cons:**

- Can fail if there are conflicts during rebase
- Rewrites commit history (force push required)
- Not ideal for PRs with more than 5 commits or complex changes

#### 3. Merge

Merges the base branch into the PR branch before applying fixes.

```bash
markdown-table-fixer github https://github.com/owner/repo/pull/123 --sync-strategy=merge
```

**Use when:**

- You want to preserve exact commit history
- Rebase fails or is not desired
- The PR has more than 5 commits or originates from a fork

**Pros:**

- Preserves all commit history
- More reliable than rebase for complex changes
- Handles unrelated histories with `--allow-unrelated-histories`

**Cons:**

- Creates a merge commit
- Can fail if there are actual content conflicts
- Less clean history than rebase

### Conflict Resolution Strategies

When syncing with the base branch, conflicts may occur. You can control how
to handle them:

#### 1. Fail (Default)

Abort if conflicts occur during sync.

```bash
markdown-table-fixer github PR_URL --sync-strategy=rebase \
  --conflict-strategy=fail
```

**Use when:**

- You want to review conflicts manually
- Safety is paramount
- You're testing in dry-run mode

#### 2. Ours

Keep PR changes, discard conflicting base changes.

```bash
markdown-table-fixer github PR_URL --sync-strategy=merge \
  --conflict-strategy=ours
```

**Use when:**

- The PR's changes should take precedence
- You're confident about the PR's content
- Conflicts occur and PR version should take precedence

#### 3. Theirs

Keep base changes, discard conflicting PR changes.

```bash
markdown-table-fixer github PR_URL --sync-strategy=merge --conflict-strategy=theirs
```

**Use when:**

- Base branch changes should take precedence
- You want to adopt latest upstream changes
- The PR needs to align with base branch updates

## Complete Examples

### Organization Scanning Examples

```bash
# Export your GitHub token
export GITHUB_TOKEN=ghp_your_token_here

# Scan and fix all blocked PRs in an organization
markdown-table-fixer github lfreleng-actions

# Dry run to see what changes would apply
markdown-table-fixer github lfreleng-actions --dry-run

# Include draft PRs in the scan
markdown-table-fixer github lfreleng-actions \
  --include-drafts

# Debug mode for testing (process first PR)
markdown-table-fixer github lfreleng-actions --debug-org

# Scan with rebase strategy for all PRs
markdown-table-fixer github lfreleng-actions --sync-strategy=rebase

# Quiet mode (minimal output)
markdown-table-fixer github lfreleng-actions --quiet
```

### Single PR Examples

```bash
# Fix with no sync (default)
markdown-table-fixer github https://github.com/owner/repo/pull/123

# Fix with rebase
markdown-table-fixer github https://github.com/owner/repo/pull/123 --sync-strategy=rebase

# Fix with merge and automatic conflict resolution
markdown-table-fixer github https://github.com/owner/repo/pull/123 \
  --sync-strategy=merge \
  --conflict-strategy=ours

# Dry run with verbose output
markdown-table-fixer github https://github.com/owner/repo/pull/123 \
  --sync-strategy=merge \
  --dry-run \
  --verbose
```

## Workflow

### Organization Scan Workflow

1. **Count repositories** - Uses lightweight GraphQL query to count total repos
2. **Scan repositories** - Iterates through all non-archived repositories
   with bounded parallelism
3. **Fetch PRs** - For each repo, fetches open PRs with status check data
4. **Analyze checks** - Identifies PRs with failing markdown/lint checks
5. **Process PRs** - For each blocked PR:
   - Clone the PR branch
   - Fix markdown table formatting issues
   - Amend and force push changes
6. **Display results** - Shows summary with fixed PR URLs

### Single PR Workflow

1. **Parse PR URL** - Extract owner, repo, and PR number
2. **Fetch PR details** - Get branch names, SHA, and clone URL via GitHub API
3. **Clone repository** - Full clone of the PR branch (not shallow)
4. **Sync with base** (if strategy != "none"):
   - **Rebase**: `git rebase origin/main`
   - **Merge**: `git merge origin/main --allow-unrelated-histories`
5. **Scan markdown files** - Find all `.md` files in the repository
6. **Check tables** - Examine each table for formatting issues
7. **Apply fixes** - Fix misaligned pipes and spacing
8. **Amend commit** - Use `git commit --amend --no-edit` to update the last commit
9. **Force push** - Push changes with `git push --force origin branch-name`
10. **Create comment** - Post a summary comment on the PR (single PR mode)

## Authentication

You must provide a GitHub token with appropriate permissions:

```bash
# Set as environment variable
export GITHUB_TOKEN=ghp_your_token_here

# Or pass directly
markdown-table-fixer github PR_URL --token ghp_your_token_here
```

**Required token permissions:**

- `repo` - Full control of private repositories (or `public_repo` for
  public repositories)
- `write:discussion` - Create comments on PRs (for single PR mode)

## Performance and Efficiency

The tool uses optimized GraphQL queries matching the proven approach from `dependamerge`:

- **Lightweight repository counting** - Fetches repo names, no PR data
- **Batched PR fetching** - Retrieves PRs with status checks in efficient batches
- **Bounded concurrency** - Limits parallel operations to avoid rate limits:
  - 8 concurrent repository scans
  - 16 concurrent page fetches
- **Real-time progress** - Shows live updates with Rich library (when available)

**Typical performance:**

- ~10 seconds to scan 78 repositories
- ~1-2 seconds per PR to fix and push
- Scales efficiently to organizations with hundreds of repositories

## Handling Conflicts

### Rebase Conflicts

If rebase fails due to conflicts, the tool will:

1. Abort the rebase automatically
2. Return an error message
3. Leave the local clone unchanged

**Solution:** Either:

- Use `--sync-strategy=merge` instead
- Use `--sync-strategy=none` and let the PR author resolve conflicts
- Use `--conflict-strategy=ours` or `--conflict-strategy=theirs` to auto-resolve
- Manually resolve conflicts in the PR before running the tool

### Merge Conflicts

If merge fails due to conflicts, the tool will:

1. Abort the merge automatically (unless using conflict strategy)
2. Apply conflict resolution when you specify `--conflict-strategy`
3. Return an error message when the tool cannot resolve conflicts
4. Leave the local clone unchanged

**Solution:**

- Use `--conflict-strategy=ours` or `--conflict-strategy=theirs`
- Use `--sync-strategy=none` if conflicts are in unrelated files
- The PR author should resolve conflicts manually first
- Merge the base branch into the PR manually, then run the tool

### Unrelated Histories

The tool uses `--allow-unrelated-histories` for merges to handle PRs with
unusual git history (e.g., from repos that were force-pushed or have
different root commits).

## Best Practices

### For Organization Scanning

1. **Start with dry-run**: Always test with `--dry-run` first on new
   organizations
2. **Use debug mode for testing**: Test with `--debug-org` to process first
   PR
3. **Watch rate limits**: The tool optimizes API usage but watch for rate
   limit warnings
4. **Review results**: Check the summary and verify fixed PRs on GitHub
5. **Schedule regular runs**: Use in CI/CD to keep tables formatted consistently

### For Single PR Fixing

1. **Start with dry-run**: Always test with `--dry-run` first to preview
   changes
2. **Use 'none' for simple cases**: If the PR is already up-to-date, skip
   syncing
3. **Prefer 'rebase' for clean PRs**: Use rebase for simple PRs with a
   small number of commits
4. **Use 'merge' for complex PRs**: Use merge for PRs with more than 5
   commits or from forks
5. **Check PR status after**: Always verify the PR looks correct on GitHub
   after pushing
6. **Handle failures appropriately**: If sync fails, fall back to
   `--sync-strategy=none`

## Troubleshooting

### Organization Scanning Issues

#### "No blocked PRs found"

- Success - no PRs have markdown/lint failures blocking them
- The organization's PRs are all passing checks

#### "Error scanning repository"

- Individual repo errors don't stop the scan
- The tool counts and reports errors in summary
- Check GitHub API permissions and rate limits

#### "Progress not updating"

- Rich library may not be available or terminal doesn't support it
- Tool shows fallback text display instead
- Install Rich for better progress display: `pip install rich`

### Single PR Issues

#### "unrelated histories" error with merge

- This is now handled automatically with `--allow-unrelated-histories`
- Indicates unusual git history in the PR

#### "refusing to merge" error with rebase

- The PR has conflicts that prevent automatic rebasing
- Solution: Use `--sync-strategy=merge` or `--sync-strategy=none`
- Or use `--conflict-strategy=ours` or `--conflict-strategy=theirs`

#### "No markdown files found"

- The repository has no `.md` files
- Nothing to fix - this outcome indicates success

#### "Files were already properly formatted"

- All tables already have proper formatting
- No changes needed - this is success

#### Force push rejected

- The PR branch received updates since cloning
- Re-run the tool to pull latest changes and try again

## What Gets Fixed

The tool fixes these table formatting issues:

- **Misaligned pipes**: Ensures all pipes align vertically across rows
- **Missing spaces**: Adds required single space after opening `|` and
  before closing `|`
- **Proper padding**: Adds appropriate padding to align content within
  columns
- **Separator formatting**: Ensures separator rows use proper dashes and colons

## What Doesn't Get Fixed

The tool intentionally does NOT:

- Change table content or text
- Reorder columns or rows
- Add or remove tables
- Fix non-table markdown issues
- Resolve merge conflicts (without conflict strategy)
- Change commit messages
- Change files other than markdown tables

## CLI Options Reference

### Common Options

- `--token`, `-t` - GitHub token (or set `GITHUB_TOKEN` env var)
- `--dry-run` - Preview changes without pushing
- `--verbose`, `-v` - Enable verbose output
- `--quiet`, `-q` - Suppress all output except errors
- `--log-level` - Set logging level (DEBUG, INFO, WARNING, ERROR)

### Organization Scanning Options

- `--include-drafts` - Include draft PRs in scan
- `--debug-org` - Process first PR found (for testing)

### Sync Options

- `--sync-strategy` - How to sync with base: `none`, `rebase`, or `merge`
  (default: `none`)
- `--conflict-strategy` - How to resolve conflicts: `fail`, `ours`, or
  `theirs` (default: `fail`)

## Exit Codes

- `0` - Success (fixes applied or no issues found)
- `1` - Failure (errors occurred during processing)

## Limitations

1. **Requires full repo clone** - Not shallow, needs complete git
   history for sync
2. **Force push required** - Rewrites PR branch history when fixing
   tables
3. **No conflict resolution without strategy** - The tool cannot
   automatically resolve conflicts without `--conflict-strategy`
4. **Amends last commit** - Does not create new commits
5. **API rate limits** - Subject to GitHub API rate limits (optimized
   but not unlimited)
6. **No cross-fork support** - Cannot push to PRs from forks without
   maintainer permission to push changes

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Fix Markdown Tables

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:  # Allow manual triggering

jobs:
  fix-tables:
    runs-on: ubuntu-latest
    steps:
      - name: Install markdown-table-fixer
        run: pip install markdown-table-fixer

      - name: Fix markdown tables in org
        run: |
          markdown-table-fixer github myorg \
            --token "${{ secrets.GITHUB_TOKEN }}"
```

### Scheduled Maintenance

```bash
#!/bin/bash
# Run daily via cron to keep tables formatted

export GITHUB_TOKEN=ghp_your_token_here

# Dry run first to check
markdown-table-fixer github myorg --dry-run

# If dry run looks good, run for real
if [ $? -eq 0 ]; then
  markdown-table-fixer github myorg
fi
```
