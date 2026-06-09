#!/usr/bin/env bash
# run-tests.sh — the retro-writer test + lint gate.
#
# What it does, in order:
#   1. shellcheck the bash scripts (bin/blog, bin/blog-export, bin/install.sh)
#   2. run pytest under coverage.py, measuring ONLY our python tool (bin/crt-theme)
#   3. print the coverage report and FAIL if crt-theme line coverage < 95%
#
# Coverage honesty: python (crt-theme) gets measured line coverage. The bash
# scripts are covered by behavior/e2e tests (invoked via subprocess) + shellcheck;
# their *line* coverage is not measured — bash has no equivalent gate here.
#
# Requirements: python3, pytest, coverage, shellcheck, wordgrinder.
# (wordgrinder-gated tests skip cleanly if it is absent; CI installs it.)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

MIN_COVERAGE=95

# Prefer module invocation so we use the active interpreter's packages.
PYTHON="${PYTHON:-python3}"

bar() { printf '\n=== %s ===\n' "$1"; }

# --- 1. shellcheck ---------------------------------------------------------

bar "shellcheck (bin/blog, bin/blog-export, bin/install.sh)"
if ! command -v shellcheck >/dev/null 2>&1; then
	echo "ERROR: shellcheck not found on PATH; install it (apt-get install shellcheck)." >&2
	exit 1
fi
shellcheck bin/blog bin/blog-export bin/install.sh
echo "shellcheck: clean"

# --- 2. pytest under coverage ----------------------------------------------

bar "pytest (under coverage)"
"$PYTHON" -m coverage erase
"$PYTHON" -m coverage run -m pytest

# --- 3. coverage report + gate ---------------------------------------------

bar "coverage report (bin/crt-theme)"
"$PYTHON" -m coverage report -m

bar "coverage gate (crt-theme >= ${MIN_COVERAGE}%)"
# `coverage report --fail-under` exits nonzero if TOTAL coverage is below the
# threshold. Our coverage config measures only bin/crt-theme, so TOTAL == the
# crt-theme percentage.
"$PYTHON" -m coverage report --fail-under="$MIN_COVERAGE" >/dev/null
echo "coverage gate: PASS (crt-theme >= ${MIN_COVERAGE}%)"

bar "ALL CHECKS PASSED"
