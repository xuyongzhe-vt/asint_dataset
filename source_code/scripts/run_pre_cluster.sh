#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../pre_cluster.py"

echo "Running pre_cluster..."
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: pre_cluster.py failed" >&2
    exit 1
fi

echo "pre_cluster completed successfully"
