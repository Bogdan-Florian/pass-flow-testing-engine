#!/bin/bash
# Batch 2: Process Payment
# Parameters: $1 = --payment-gateway=mock, $2 = --timeout=30

echo "[BATCH2] Starting payment processing..."
echo "[BATCH2] Parameter 1: $1"
echo "[BATCH2] Parameter 2: $2"
echo "[BATCH2] Connecting to payment gateway..."
sleep 1
echo "[BATCH2] Payment processed successfully."
exit 0
