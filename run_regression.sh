#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASELINE_FILE="${ROOT_DIR}/regression_baseline.sample.json"
OUTPUT_FILE="${ROOT_DIR}/regression_results.json"

python "${ROOT_DIR}/regression_suite.py" \
  --baseline "${BASELINE_FILE}" \
  --output "${OUTPUT_FILE}" \
  "$@"

echo "Regression suite passed."
