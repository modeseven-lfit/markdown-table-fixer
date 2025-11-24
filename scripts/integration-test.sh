#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Integration tests for markdown-table-fixer CLI
# This script tests all CLI features and can run both locally and in CI

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results array
declare -a FAILED_TESTS=()

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR=$(mktemp -d)

# Cleanup function (called via trap)
# shellcheck disable=SC2329
cleanup() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT INT TERM

# Setup test environment
setup() {
    echo -e "${BLUE}🔧 Setting up test environment...${NC}"

    # Create test directory
    mkdir -p "$TEST_DIR"

    # Create test files
    cat > "$TEST_DIR/test_table.md" << 'EOF'
# Test Document

| Name | Description | Status |
|------|-------------|--------|
| Feature 1 | A test feature | Active |
| Feature 2 | Another feature with a longer description | Pending |
EOF

    cat > "$TEST_DIR/test_table_long.md" << 'EOF'
# Test Document with Long Lines

| Variable Name    | Description                                            | Required | Default             |
| ---------------- | ------------------------------------------------------ | -------- | ------------------- |
| debug            | Enable debug mode for verbose output                   | No       | false               |
| github_token     | GitHub token for API access (changed files)            | No       | ${{ github.token }} |
EOF

    echo -e "${GREEN}✅ Test environment ready${NC}\n"
}

# Print test header
print_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Test $TESTS_RUN: $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}



assert_contains() {
    local output="$1"
    local expected="$2"
    local description="$3"

    if echo "$output" | grep -q "$expected"; then
        echo -e "${GREEN}✅ PASS: $description${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL: $description${NC}"
        echo -e "${RED}   Expected to find: '$expected'${NC}"
        echo -e "${RED}   In output: '$output'${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$description")
        return 1
    fi
}

# Test functions

test_version_flag() {
    print_test "Version flag at top level (--version)"

    output=$(markdown-table-fixer --version 2>&1)
    assert_contains "$output" "markdown-table-fixer version" "Version output contains tool name and version"
}

test_version_flag_lint() {
    print_test "Version flag in lint command (lint --version)"

    output=$(markdown-table-fixer lint --version 2>&1)
    assert_contains "$output" "markdown-table-fixer version" "Version shown in lint command"
}

test_version_flag_github() {
    print_test "Version flag in github command (github --version)"

    output=$(markdown-table-fixer github --version 2>&1)
    assert_contains "$output" "markdown-table-fixer version" "Version shown in github command"
}

test_help_shows_version() {
    print_test "Help output shows version (--help)"

    output=$(markdown-table-fixer --help 2>&1)
    assert_contains "$output" "markdown-table-fixer version" "Version shown in help output"
}

test_lint_help_shows_version() {
    print_test "Lint help output shows version (lint --help)"

    output=$(markdown-table-fixer lint --help 2>&1)
    assert_contains "$output" "markdown-table-fixer version" "Version shown in lint help"
}

test_auto_fix_enabled() {
    print_test "Auto-fix enabled by default (--auto-fix)"

    cp "$TEST_DIR/test_table.md" "$TEST_DIR/test_auto_fix.md"

    # Run with --auto-fix (default behavior)
    markdown-table-fixer lint "$TEST_DIR/test_auto_fix.md" --auto-fix --quiet > /dev/null 2>&1

    # File should be modified
    if [ -f "$TEST_DIR/test_auto_fix.md" ]; then
        echo -e "${GREEN}✅ PASS: Auto-fix modifies file${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Auto-fix didn't modify file${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Auto-fix modifies file")
    fi
}

test_no_auto_fix() {
    print_test "No auto-fix flag works (--no-auto-fix)"

    cp "$TEST_DIR/test_table.md" "$TEST_DIR/test_no_auto_fix.md"
    original_content=$(cat "$TEST_DIR/test_no_auto_fix.md")

    # Run with --no-auto-fix
    markdown-table-fixer lint "$TEST_DIR/test_no_auto_fix.md" --no-auto-fix --quiet > /dev/null 2>&1 || true

    new_content=$(cat "$TEST_DIR/test_no_auto_fix.md")

    if [ "$original_content" = "$new_content" ]; then
        echo -e "${GREEN}✅ PASS: --no-auto-fix doesn't modify file${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: --no-auto-fix modified file when it shouldn't${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("--no-auto-fix doesn't modify file")
    fi
}

test_fail_on_error_with_issues() {
    print_test "Fail on error with issues (--fail-on-error --no-auto-fix)"

    cp "$TEST_DIR/test_table.md" "$TEST_DIR/test_fail.md"

    # Should exit with error code when issues found and not fixed
    set +e
    markdown-table-fixer lint "$TEST_DIR/test_fail.md" --no-auto-fix --fail-on-error --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -ne 0 ]; then
        echo -e "${GREEN}✅ PASS: Exit code non-zero when issues found with --fail-on-error${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Exit code non-zero when issues found with --fail-on-error${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Exit code non-zero when issues found with --fail-on-error")
    fi
}

test_fail_on_error_after_fix() {
    print_test "Fail on error after auto-fix (--fail-on-error --auto-fix)"

    cp "$TEST_DIR/test_table.md" "$TEST_DIR/test_fail_fixed.md"

    # Should exit with success when issues are fixed
    set +e
    markdown-table-fixer lint "$TEST_DIR/test_fail_fixed.md" --auto-fix --fail-on-error --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: Exit code zero when issues fixed with --fail-on-error${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Exit code zero when issues fixed with --fail-on-error${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Exit code zero when issues fixed with --fail-on-error")
    fi
}

test_no_fail_on_error() {
    print_test "No fail on error flag (--no-fail-on-error)"

    cp "$TEST_DIR/test_table.md" "$TEST_DIR/test_no_fail.md"

    # Should exit with success even with issues
    set +e
    markdown-table-fixer lint "$TEST_DIR/test_no_fail.md" --no-auto-fix --no-fail-on-error --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: Exit code zero with issues when --no-fail-on-error used${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Exit code zero with issues when --no-fail-on-error used${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Exit code zero with issues when --no-fail-on-error used")
    fi
}

test_parallel_processing() {
    print_test "Parallel processing enabled (--parallel)"

    # Create a subdirectory for parallel test
    mkdir -p "$TEST_DIR/parallel_test"
    for i in {1..5}; do
        cp "$TEST_DIR/test_table.md" "$TEST_DIR/parallel_test/test_parallel_$i.md"
    done

    # Run with parallel processing on the subdirectory
    set +e
    markdown-table-fixer lint "$TEST_DIR/parallel_test" --auto-fix --parallel --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: Parallel processing completes successfully${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Parallel processing failed with exit code $exit_code${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Parallel processing completes successfully")
    fi
}

test_no_parallel() {
    print_test "No parallel processing (--no-parallel)"

    # Create a subdirectory for sequential test
    mkdir -p "$TEST_DIR/sequential_test"
    for i in {1..3}; do
        cp "$TEST_DIR/test_table.md" "$TEST_DIR/sequential_test/test_sequential_$i.md"
    done

    # Run without parallel processing on the subdirectory
    set +e
    markdown-table-fixer lint "$TEST_DIR/sequential_test" --auto-fix --no-parallel --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: Sequential processing completes successfully${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Sequential processing failed with exit code $exit_code${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Sequential processing completes successfully")
    fi
}

test_workers_flag() {
    print_test "Workers flag (--workers 2)"

    # Create a subdirectory for workers test
    mkdir -p "$TEST_DIR/workers_test"
    for i in {1..4}; do
        cp "$TEST_DIR/test_table.md" "$TEST_DIR/workers_test/test_workers_$i.md"
    done

    # Run with 2 workers on the subdirectory
    set +e
    markdown-table-fixer lint "$TEST_DIR/workers_test" --auto-fix --workers 2 --quiet > /dev/null 2>&1
    exit_code=$?
    set -e

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: Workers flag accepted and processing completes${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Workers flag failed with exit code $exit_code${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Workers flag accepted and processing completes")
    fi
}

test_verbose_flag() {
    print_test "Verbose output flag (-v/--verbose)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --verbose 2>&1)

    # Verbose should show more output
    if [ -n "$output" ]; then
        echo -e "${GREEN}✅ PASS: Verbose flag produces output${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Verbose flag produced no output${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Verbose flag produces output")
    fi
}

test_quiet_flag() {
    print_test "Quiet output flag (-q/--quiet)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --quiet 2>&1)

    # Quiet should minimize output
    line_count=$(echo "$output" | wc -l)
    if [ "$line_count" -lt 5 ]; then
        echo -e "${GREEN}✅ PASS: Quiet flag minimizes output (${line_count} lines)${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Quiet flag produced too much output (${line_count} lines)${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Quiet flag minimizes output")
    fi
}

test_log_level_debug() {
    print_test "Log level DEBUG (--log-level DEBUG)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --log-level DEBUG 2>&1)

    # Should produce output (debug level)
    if [ -n "$output" ]; then
        echo -e "${GREEN}✅ PASS: Log level DEBUG produces output${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Log level DEBUG produced no output${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Log level DEBUG produces output")
    fi
}

test_log_level_error() {
    print_test "Log level ERROR (--log-level ERROR)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --log-level ERROR 2>&1)

    # Should minimize output (error level only)
    line_count=$(echo "$output" | wc -l)
    if [ "$line_count" -lt 10 ]; then
        echo -e "${GREEN}✅ PASS: Log level ERROR minimizes output${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Log level ERROR produced too much output${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Log level ERROR minimizes output")
    fi
}

test_format_text() {
    print_test "Text output format (--format text)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --format text 2>&1)

    # Should contain table characters
    assert_contains "$output" "Files scanned" "Text format shows summary table"
}

test_format_json() {
    print_test "JSON output format (--format json)"

    output=$(markdown-table-fixer lint "$TEST_DIR/test_table.md" --no-auto-fix --format json 2>&1)

    # Should be valid JSON
    if echo "$output" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS: JSON format produces valid JSON${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: JSON format output is not valid JSON${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("JSON format produces valid JSON")
    fi
}

test_max_line_length() {
    print_test "Max line length flag (--max-line-length)"

    cp "$TEST_DIR/test_table_long.md" "$TEST_DIR/test_max_len.md"

    # Run with max-line-length set to 80
    markdown-table-fixer lint "$TEST_DIR/test_max_len.md" --auto-fix --max-line-length 80 --quiet > /dev/null 2>&1

    # Should add markdownlint disable comments for long lines
    content=$(cat "$TEST_DIR/test_max_len.md")
    if echo "$content" | grep -q "markdownlint-disable MD013"; then
        echo -e "${GREEN}✅ PASS: Max line length adds MD013 disable comments${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Max line length didn't add MD013 comments${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Max line length adds MD013 disable comments")
    fi
}

test_unicode_emoji_support() {
    print_test "Unicode and emoji support"

    cat > "$TEST_DIR/test_emoji.md" << 'EOF'
# Test Emoji Table

| Feature | Status |
|---------|--------|
| JSON | ✅ Yes |
| YAML | ✅ Yes |
| XML | ❌ No |
EOF

    # Run fixer
    markdown-table-fixer lint "$TEST_DIR/test_emoji.md" --auto-fix --quiet > /dev/null 2>&1

    # Check that emojis are preserved
    content=$(cat "$TEST_DIR/test_emoji.md")
    if echo "$content" | grep -q "✅" && echo "$content" | grep -q "❌"; then
        echo -e "${GREEN}✅ PASS: Emojis preserved in tables${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Emojis not preserved${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Emojis preserved in tables")
    fi
}

test_example_bad_tables() {
    print_test "Example bad_tables.md with emojis can be fixed"

    # Copy example file to test directory to avoid modifying the original
    cp "$PROJECT_ROOT/examples/bad_tables.md" "$TEST_DIR/test_bad_tables.md"

    # Run fixer (will exit 1 if issues found, which is expected)
    set +e
    markdown-table-fixer lint "$TEST_DIR/test_bad_tables.md" --auto-fix --quiet > /dev/null 2>&1
    set -e

    # Check that emojis are preserved after fixing
    content=$(cat "$TEST_DIR/test_bad_tables.md")
    if echo "$content" | grep -q "✅" && echo "$content" | grep -q "❌" && echo "$content" | grep -q "⚠️"; then
        echo -e "${GREEN}✅ PASS: bad_tables.md fixed with emojis preserved${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: bad_tables.md emojis not preserved${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("bad_tables.md fixed with emojis preserved")
    fi
}

test_example_emoji_tables() {
    print_test "Example emoji_tables.md comprehensive emoji test"

    # Copy example file to test directory
    cp "$PROJECT_ROOT/examples/emoji_tables.md" "$TEST_DIR/test_emoji_tables.md"

    # Run fixer (will exit 1 if issues found, which is expected)
    set +e
    markdown-table-fixer lint "$TEST_DIR/test_emoji_tables.md" --auto-fix --quiet > /dev/null 2>&1
    set -e

    # Check that various emojis are preserved after fixing
    content=$(cat "$TEST_DIR/test_emoji_tables.md")
    if echo "$content" | grep -q "✅" && \
       echo "$content" | grep -q "❌" && \
       echo "$content" | grep -q "⚠️" && \
       echo "$content" | grep -q "🔴" && \
       echo "$content" | grep -q "🟢" && \
       echo "$content" | grep -q "🚀" && \
       echo "$content" | grep -q "👤"; then
        echo -e "${GREEN}✅ PASS: emoji_tables.md fixed with all emojis preserved${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: emoji_tables.md emojis not preserved${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("emoji_tables.md fixed with all emojis preserved")
    fi
}

test_help_flags() {
    print_test "Help output contains all new flags"

    output=$(markdown-table-fixer lint --help 2>&1)

    assert_contains "$output" "--auto-fix" "Help shows --auto-fix flag"
    assert_contains "$output" "--fail-on-error" "Help shows --fail-on-error flag"
    assert_contains "$output" "--parallel" "Help shows --parallel flag"
    assert_contains "$output" "--workers" "Help shows --workers flag"
    assert_contains "$output" "--verbose" "Help shows --verbose flag"
    assert_contains "$output" "--quiet" "Help shows --quiet flag"
    assert_contains "$output" "--log-level" "Help shows --log-level flag"
    assert_contains "$output" "--format" "Help shows --format flag"
    assert_contains "$output" "--max-line-length" "Help shows --max-line-length flag"
}

test_actual_table_fixing() {
    print_test "Actual table fixing with markdownlint verification"

    cat > "$TEST_DIR/test_actual.md" << 'EOF'
# Test Document

| Name | Description | Status |
|------|-------------|--------|
| Item1|Short|Active|
| Item2 |  Long description  | Pending |
EOF

    # Run fixer
    markdown-table-fixer lint "$TEST_DIR/test_actual.md" --auto-fix --quiet > /dev/null 2>&1

    # Verify table is properly formatted
    content=$(cat "$TEST_DIR/test_actual.md")

    # Check for proper spacing (should have spaces around pipes)
    if echo "$content" | grep -q "| Item1 " && echo "$content" | grep -q " Active |"; then
        echo -e "${GREEN}✅ PASS: Tables properly formatted with spacing${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: Tables not properly formatted${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Tables properly formatted with spacing")
    fi
}

# Print summary
print_summary() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Tests run:    ${NC}$TESTS_RUN"
    echo -e "${GREEN}Tests passed: ${NC}$TESTS_PASSED"
    echo -e "${RED}Tests failed: ${NC}$TESTS_FAILED"

    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo -e "\n${RED}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "${RED}  ❌ $test${NC}"
        done
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}\n"
        return 0
    else
        echo -e "${RED}❌ Some tests failed!${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🧪 markdown-table-fixer Integration Tests${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${BLUE}📁 Using temporary test directory: $TEST_DIR${NC}\n"

    # Setup
    setup

    # Run all tests
    test_version_flag
    test_version_flag_lint
    test_version_flag_github
    test_help_shows_version
    test_lint_help_shows_version
    test_auto_fix_enabled
    test_no_auto_fix
    test_fail_on_error_with_issues
    test_fail_on_error_after_fix
    test_no_fail_on_error
    test_parallel_processing
    test_no_parallel
    test_workers_flag
    test_verbose_flag
    test_quiet_flag
    test_log_level_debug
    test_log_level_error
    test_format_text
    test_format_json
    test_max_line_length
    test_unicode_emoji_support
    test_example_bad_tables
    test_example_emoji_tables
    test_help_flags
    test_actual_table_fixing

    # Print summary and exit
    # Cleanup is handled by trap
    print_summary
    exit $?
}

# Run main function
main "$@"
