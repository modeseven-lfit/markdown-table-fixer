#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Helper script to test GitHub PR markdown table fixing
# Usage:
#   ./test-github-pr.sh <pr-url> [--dry-run] [--verbose] [--sync-strategy=<strategy>]
#
# Examples:
#   ./test-github-pr.sh https://github.com/owner/repo/pull/123
#   ./test-github-pr.sh https://github.com/owner/repo/pull/123 --dry-run
#   ./test-github-pr.sh https://github.com/owner/repo/pull/123 --verbose
#   ./test-github-pr.sh https://github.com/owner/repo/pull/123 --sync-strategy=rebase
#   ./test-github-pr.sh https://github.com/owner/repo/pull/123 --sync-strategy=merge

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Check if PR URL is provided
if [ $# -lt 1 ]; then
    print_msg "$RED" "Error: PR URL required"
    echo
    echo "Usage: $0 <pr-url> [--dry-run] [--verbose] [--sync-strategy=<strategy>]"
    echo
    echo "Examples:"
    echo "  $0 https://github.com/owner/repo/pull/123"
    echo "  $0 https://github.com/owner/repo/pull/123 --dry-run"
    echo "  $0 https://github.com/owner/repo/pull/123 --verbose"
    echo "  $0 https://github.com/owner/repo/pull/123 --sync-strategy=rebase"
    echo "  $0 https://github.com/owner/repo/pull/123 --sync-strategy=merge"
    echo
    echo "Sync strategies:"
    echo "  none   - Fix tables as-is without syncing (default)"
    echo "  rebase - Rebase PR onto base branch before fixing"
    echo "  merge  - Merge base branch into PR before fixing"
    exit 1
fi

PR_URL=$1
shift

# Build command with additional flags
CMD=(markdown-table-fixer github "$PR_URL" --auto-fix)

# Add any additional flags
for arg in "$@"; do
    CMD+=("$arg")
done

# Check for GitHub token
if [ -z "${GITHUB_TOKEN:-}" ]; then
    print_msg "$RED" "Error: GITHUB_TOKEN environment variable not set"
    echo
    echo "Please set your GitHub token:"
    echo "  export GITHUB_TOKEN=ghp_..."
    exit 1
fi

# Validate PR URL format
if ! echo "$PR_URL" | grep -qE '^https?://github\.com/[^/]+/[^/]+/pull/[0-9]+$'; then
    print_msg "$RED" "Error: Invalid PR URL format"
    echo
    echo "Expected format: https://github.com/owner/repo/pull/123"
    exit 1
fi

# Extract owner, repo, and PR number for display
OWNER=$(echo "$PR_URL" | sed -E 's#https?://github\.com/([^/]+)/.*#\1#')
REPO=$(echo "$PR_URL" | sed -E 's#https?://github\.com/[^/]+/([^/]+)/.*#\1#')
PR_NUMBER=$(echo "$PR_URL" | sed -E 's#.*/pull/([0-9]+).*#\1#')

print_msg "$BLUE" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_msg "$BLUE" "  Markdown Table Fixer - GitHub PR Test"
print_msg "$BLUE" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
print_msg "$GREEN" "Repository: $OWNER/$REPO"
print_msg "$GREEN" "PR Number:  #$PR_NUMBER"
print_msg "$GREEN" "PR URL:     $PR_URL"
echo

# Check if --dry-run is specified
if [[ " ${CMD[*]} " =~ " --dry-run " ]]; then
    print_msg "$YELLOW" "Mode: DRY RUN (no changes will be pushed)"
else
    print_msg "$YELLOW" "Mode: LIVE (changes will be pushed to GitHub)"
fi

echo
print_msg "$BLUE" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Run the command
if "${CMD[@]}"; then
    echo
    print_msg "$GREEN" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_msg "$GREEN" "  ✅ Success!"
    print_msg "$GREEN" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    if [[ " ${CMD[*]} " =~ " --dry-run " ]]; then
        print_msg "$YELLOW" "This was a dry run. To apply changes, run without --dry-run:"
        echo "  $0 $PR_URL"
    else
        print_msg "$GREEN" "Changes have been pushed to GitHub!"
        echo
        echo "View the PR at:"
        echo "  $PR_URL"
    fi
    exit 0
else
    EXIT_CODE=$?
    echo
    print_msg "$RED" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_msg "$RED" "  ❌ Failed (exit code: $EXIT_CODE)"
    print_msg "$RED" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit $EXIT_CODE
fi
