#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(dirname "$0")/../crawling.py"

rm -rf ${BASE_DIR}/crawling
mkdir ${BASE_DIR}/crawling

ssh "${REMOTE_CRAWL_HOST}" <<'EOF'
rm -rf ${BASE_DIR}/crawling/
mkdir ${BASE_DIR}/crawling
EOF

cp ${BASE_DIR}/metadata/org_1.json ${BASE_DIR}/crawling/org.json

scp ${BASE_DIR}/metadata/org_2.json "${REMOTE_CRAWL_HOST}":${BASE_DIR}/crawling/org.json

echo "Running script..."

screen -S crawl -X stuff $'cd '"${PROJECT_ROOT}"$'\n'
screen -S crawl -X stuff $'python3 crawling.py --log_file "log_1.log"\n'

ssh "${REMOTE_CRAWL_HOST}" <<EOF
screen -S crawl -X stuff \$'cd ${PROJECT_ROOT}\n'
screen -S crawl -X stuff \$'python3 crawling.py --log_file "log_2.log"\n'
EOF
