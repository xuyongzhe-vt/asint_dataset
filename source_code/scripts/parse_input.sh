#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../parse_as_to_org_mapping.py"

echo "Running AS-to-Org parser..."
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: parse_as_to_org_mapping.py failed" >&2
    exit 1
fi

echo "AS-to-Org parser completed successfully"
