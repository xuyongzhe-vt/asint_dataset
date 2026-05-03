#!/bin/bash
set -euo pipefail

RUN_DATE="20260315"   # e.g. "20260220"  (YYYYMMDD) ; empty => today

SRC_DIR="${IRR_SRC_DIR:-/path/to/irrs/compressed}"
DST_DIR="${BASE_DIR}/input"
OUT_DIR="${BASE_DIR}/output"
WHOIS_IPS_DIR="${WHOIS_IPS_SRC_DIR:-/path/to/whois-ips}"

mkdir -p ${BASE_DIR}/
mkdir -p "$DST_DIR" "$OUT_DIR"

die() {
  echo "Error: $*" >&2
  exit 1
}

copy_or_die() {
  local src="$1"
  local dst="$2"
  local label="$3"
  [[ -f "$src" ]] || die "Missing $label: $src"
  echo "Source ($label): $src"
  echo " -> Dest ($label): $dst"
  cp "$src" "$dst"
}

target_date=""
if [[ -n "${RUN_DATE}" ]]; then
  target_date="${RUN_DATE}"
elif [[ $# -ge 1 && -n "${1:-}" ]]; then
  target_date="$1"
else
  target_date="$(date +%Y%m%d)"
fi

[[ "$target_date" =~ ^[0-9]{8}$ ]] || die "RUN_DATE (or arg) must be YYYYMMDD, got: $target_date"

date_iso="${target_date:0:4}-${target_date:4:2}-${target_date:6:2}"
date -d "$date_iso" >/dev/null 2>&1 || die "Invalid date: $target_date"

data_date="$target_date"                         # daily snapshots
month_first="$(date -d "$date_iso" +%Y%m01)"     # first day of month (for ARIN/APNIC/CAIDA monthly)
year="$(date -d "$date_iso" +%Y)"
month="$(date -d "$date_iso" +%m)"
day="$(date -d "$date_iso" +%d)"

echo "Run date (daily snapshots): $data_date"
echo "Month bucket (YYYYMM01):    $month_first"
echo "Writing date.txt -> $DST_DIR/date.txt"
echo "$data_date" > "$DST_DIR/date.txt"

echo
echo "=== WHOIS snapshots (local copies) ==="
echo "IRR compressed snapshot source dir: $SRC_DIR"
echo "Destination input dir:              $DST_DIR"
echo

copy_or_die "$SRC_DIR/${data_date}_lacnic.whois.db.gz" "$DST_DIR/lacnic.db.gz"  "LACNIC"
copy_or_die "$SRC_DIR/${data_date}_afrinic.db.gz"      "$DST_DIR/afrinic.db.gz" "AFRINIC"
copy_or_die "$SRC_DIR/${data_date}_ripe.db.gz"         "$DST_DIR/ripe.db.gz"    "RIPE"
copy_or_die "$SRC_DIR/${data_date}_jpirr.db.gz"        "$DST_DIR/jpirr.db.gz"   "JPIRR"

echo
echo "=== ARIN snapshot (monthly directory) ==="
arin_src="${WHOIS_IPS_DIR}/arin/${month_first}/arin_db.txt"
echo "ARIN source dir: $(dirname "$arin_src")"
copy_or_die "$arin_src" "$DST_DIR/arin_db.txt" "ARIN (txt)"

echo "Compressing ARIN -> $DST_DIR/arin.db.gz"
gzip -f "$DST_DIR/arin_db.txt"
mv -f "$DST_DIR/arin_db.txt.gz" "$DST_DIR/arin.db.gz"
echo "ARIN final: $DST_DIR/arin.db.gz"

echo
echo "=== APNIC snapshot (monthly directory) ==="
apnic_src="${WHOIS_IPS_DIR}/apnic/${month_first}/APNIC/apnic.RPSL.db.gz"
echo "APNIC source dir: $(dirname "$apnic_src")"
copy_or_die "$apnic_src" "$DST_DIR/apnic.db.gz" "APNIC"

echo
echo "WHOIS paste ready"
echo

caida_url="https://publicdata.caida.org/datasets/as-organizations/${month_first}.as-org2info.jsonl.gz"
peeringdb_url="https://publicdata.caida.org/datasets/peeringdb/${year}/${month}/peeringdb_2_dump_${year}_${month}_${day}.json"

echo "=== External datasets (downloads) ==="

echo "Source (CAIDA URL): $caida_url"
echo " -> Dest (CAIDA):   $DST_DIR/caida.jsonl"
if ! wget --no-check-certificate -q --tries=1 --timeout=30 -O - "$caida_url" | gunzip -c > "$DST_DIR/caida.jsonl"; then
  die "Failed to fetch or decompress CAIDA: $caida_url"
fi

echo "Source (PeeringDB URL): $peeringdb_url"
echo " -> Dest (PeeringDB):   $DST_DIR/peeringdb.json"
if ! wget --no-check-certificate -q --tries=1 --timeout=30 -O "$DST_DIR/peeringdb.json" "$peeringdb_url"; then
  die "Failed to fetch PeeringDB: $peeringdb_url"
fi

echo
echo "Saved:"
echo " - $DST_DIR/lacnic.db.gz"
echo " - $DST_DIR/afrinic.db.gz"
echo " - $DST_DIR/ripe.db.gz"
echo " - $DST_DIR/jpirr.db.gz"
echo " - $DST_DIR/arin.db.gz"
echo " - $DST_DIR/apnic.db.gz"
echo " - $DST_DIR/caida.jsonl"
echo " - $DST_DIR/peeringdb.json"
