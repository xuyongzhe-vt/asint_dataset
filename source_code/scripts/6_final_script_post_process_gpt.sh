#!/bin/bash

set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../final_process.py"

rm -rf ${BASE_DIR}/final_output/
mkdir ${BASE_DIR}/final_output/

echo "Final parsing"
if ! python3 "$SCRIPT_PATH"; then
    echo "Error: final_process.py.py failed" >&2
    exit 1
fi

echo "Final parsing completed successfully"
