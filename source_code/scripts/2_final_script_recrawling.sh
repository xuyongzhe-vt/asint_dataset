#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../crawling.py"

echo "Running script..."

screen -S crawl -X stuff $'cd '"${PROJECT_ROOT}"$'\n'
screen -S crawl -X stuff $'python3 crawling.py --log_file "log_1.log"\n'

ssh "${REMOTE_CRAWL_HOST}" <<EOF
screen -S crawl -X stuff \$'cd ${PROJECT_ROOT}\n'
screen -S crawl -X stuff \$'python3 crawling.py --log_file "log_2.log"\n'
EOF
