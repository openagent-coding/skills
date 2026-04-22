#!/bin/bash
# parse_scores.sh — Extract the last machine-readable SCORES block from an evaluation report.
# Usage: bash scripts/parse_scores.sh <report-file>
# Output: JSON object on stdout, e.g. {"completeness":4,"groundedness":3,...}
# Exit codes: 0 = success, 1 = no scores found, 2 = file not found

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <report-file>" >&2
  exit 2
fi

REPORT_FILE="$1"

if [ ! -f "$REPORT_FILE" ]; then
  echo "Error: file not found: $REPORT_FILE" >&2
  exit 2
fi

# Extract the last SCORES line, strip the HTML comment wrapper, output clean JSON.
SCORES_LINE=$(grep '<!-- SCORES:' "$REPORT_FILE" | tail -1)

if [ -z "$SCORES_LINE" ]; then
  echo "Error: no SCORES block found in $REPORT_FILE" >&2
  exit 1
fi

echo "$SCORES_LINE" | sed 's/.*<!-- SCORES://;s/ *-->.*//'
