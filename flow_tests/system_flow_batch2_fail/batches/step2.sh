#!/usr/bin/env sh
set -e

echo "Step 2 starting"
for i in 1 2; do
  sleep 1
  echo "Step 2 progress ${i}0%"
done

echo "Step 2 failed"
exit 2
