#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../split_orgs_to_crawl.py"

mkdir ${BASE_DIR}/metadata

echo "Split works to two files..."
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: split_orgs_to_crawl.py failed" >&2
    exit 1
fi

echo "Splitting completed successfully"
