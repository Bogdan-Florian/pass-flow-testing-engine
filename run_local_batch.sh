#!/usr/bin/env bash
set -euo pipefail

# This script processes the first .csv/.xlsx/.xls file found in the local "input" folder.
# Adjust logic as needed for real batches.

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
INPUT_DIR="$SCRIPT_DIR/input"

if [ ! -d "$INPUT_DIR" ]; then
  echo "ERROR: input directory not found: $INPUT_DIR" >&2
  exit 1
fi

# Pick the first matching file
file=""
for f in "$INPUT_DIR"/*.csv "$INPUT_DIR"/*.xlsx "$INPUT_DIR"/*.xls; do
  if [ -f "$f" ]; then
    file="$f"
    break
  fi
done

if [ -z "$file" ]; then
  echo "No CSV/XLSX/XLS files found in $INPUT_DIR"
  exit 1
fi

echo "Processing file: $file"
# Example processing: count lines and print file info
wc -l "$file"
ls -l "$file"

# Simulate some work
sleep 1
echo "Done"
exit 0
