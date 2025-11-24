#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Demo script for markdown-table-fixer
# Shows the tool's capabilities for detecting and fixing table formatting issues

set -e

echo "🛠️  Markdown Table Fixer Demo"
echo "=============================="
echo ""

# Check if tool is installed
if ! command -v markdown-table-fixer &> /dev/null; then
    echo "❌ markdown-table-fixer is not installed"
    echo "   Install it with: pip install -e ."
    exit 1
fi

echo "✅ markdown-table-fixer is installed"
echo ""

# Check if example file exists
if [ ! -f "examples/bad_tables.md" ]; then
    echo "❌ Example file not found: examples/bad_tables.md"
    exit 1
fi

echo "📝 Example file: examples/bad_tables.md"
echo ""

# Create a backup
cp examples/bad_tables.md examples/bad_tables.md.backup

echo "Step 1: Scan for issues (without fixing)"
echo "-----------------------------------------"
echo ""
markdown-table-fixer lint examples/bad_tables.md || true
echo ""

read -r -p "Press Enter to continue and fix the issues..."
echo ""

echo "Step 2: Fix the issues"
echo "----------------------"
echo ""
markdown-table-fixer lint examples/bad_tables.md --fix
echo ""

echo "Step 3: Verify the fix"
echo "----------------------"
echo ""
echo "Running scan again to verify all issues are fixed..."
markdown-table-fixer lint examples/bad_tables.md
echo ""

echo "✅ All issues fixed!"
echo ""
echo "You can view the fixed file at: examples/bad_tables.md"
echo "The original file was backed up to: examples/bad_tables.md.backup"
echo ""

# Restore from backup
echo "Restoring original file for next demo run..."
mv examples/bad_tables.md.backup examples/bad_tables.md

echo ""
echo "Demo complete! 🎉"
