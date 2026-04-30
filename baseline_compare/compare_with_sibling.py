import json
from pathlib import Path

from asint_loader import load_asint_dataset
from compare import compare_dataset

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE_FILE = ROOT / "baseline-2025-09" / "as_sibling.json"
OUTPUT_DIR = HERE / "sibling"

def load_candidate():
    with open(CANDIDATE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("data", data)
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for k, entry in records.items():
        try:
            kk = int(k)
        except (TypeError, ValueError):
            continue
        parent.setdefault(kk, kk)
        for s in entry.get("Sibling ASNs", []) or []:
            try:
                a = int(s)
            except (TypeError, ValueError):
                continue
            parent.setdefault(a, a)
            union(kk, a)

    clusters = {}
    for a in parent:
        clusters.setdefault(find(a), []).append(a)
    return list(clusters.values())

def main():
    asint_families, asn_to_name = load_asint_dataset()
    candidate_families = load_candidate()
    compare_dataset(asint_families, candidate_families, asn_to_name, str(OUTPUT_DIR))
    print(f"Wrote comparison to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
