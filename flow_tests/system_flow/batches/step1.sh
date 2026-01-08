#!/usr/bin/env sh
set -e

echo "Step 1 starting"
for i in 1 2 3 4 5; do
  sleep 1
  echo "Step 1 progress ${i}0%"
done

echo "Step 1 complete"
exit 0
