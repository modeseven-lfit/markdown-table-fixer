<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Integration Tests

This directory contains integration test scripts for `markdown-table-fixer`.

## Running Tests

### Locally

Run the integration test script:

```bash
bash scripts/integration-test.sh
```

This will:

- Create a temporary directory for test files using `mktemp`
- Run all integration tests
- Clean up the temporary directory automatically on exit

### In CI

The GitHub Actions workflow automatically runs these tests:

```yaml
- name: Run integration tests
  run: bash scripts/integration-test.sh
```

## Test Coverage

The integration tests cover:

- Version flag functionality
- Auto-fix and no-auto-fix modes
- Fail-on-error behavior
- Parallel and sequential processing
- Worker count configuration
- Verbose, quiet, and log-level output modes
- Output formats (text and JSON)
- Max line length configuration
- Unicode and emoji support
- Example file fixing with emoji preservation
- Help output and flag documentation
- Actual table fixing functionality

## Test Structure

Each test function:

1. Sets up test files in a temporary directory
2. Runs `markdown-table-fixer` with specific flags
3. Verifies expected behavior
4. Reports pass/fail status

## Adding New Tests

To add a new test:

1. Create a new test function following the naming convention `test_*`
2. Use `print_test "Test description"` to announce the test
3. Set up test files as needed
4. Run the CLI tool
5. Verify the results
6. Update pass/fail counters
7. Add the function call to the `main()` function

Example:

```bash
test_new_feature() {
    print_test "New feature works as expected"

    # Setup
    cat > "$TEST_DIR/test.md" << 'EOFTEST'
| Column | Value |
| ------ | ----- |
| Test   | Data  |
EOFTEST

    # Run CLI
    set +e
    markdown-table-fixer lint "$TEST_DIR/test.md" --new-flag
    exit_code=$?
    set -e

    # Verify
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: New feature test${NC}\n"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL: New feature test${NC}\n"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("New feature test")
    fi
}
```

## Temporary Directory

Tests use `mktemp -d` to create a temporary directory that is:

- Unique per test run
- Automatically cleaned up via `trap` on exit
- Outside the git repository to avoid conflicts
- Properly handled on script termination (EXIT, INT, TERM signals)

## Exit Codes

The integration test script exits with:

- `0` if all tests pass
- `1` if any test fails

This allows CI/CD systems to properly detect test failures.
