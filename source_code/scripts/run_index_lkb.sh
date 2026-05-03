#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../index_lkb.py"

echo "Running index_lkb..."
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: index_lkb.py failed" >&2
    exit 1
fi

echo "index_lkb completed successfully"
