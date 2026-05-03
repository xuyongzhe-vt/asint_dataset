set -euo pipefail

TARGET="2026-02"
BASE="$(dirname "${BASE_DIR%/}")"
SRC="$BASE/newest"
DST="$BASE/$TARGET"

if [ -e "$DST" ]; then
    echo "ERROR: $DST already exists" >&2
    exit 1
fi

mv "$SRC" "$DST"
cd "$DST"

FAIL=0
for d in crawling input llm metadata output; do
    tar -czf "${d}.tar.gz" "$d" || FAIL=1 &
done

wait  # wait for all background tars

if [ "$FAIL" -ne 0 ]; then
    echo "ERROR: One or more tarballs failed. Not removing directories." >&2
    exit 1
fi

rm -rf crawling input metadata output llm
