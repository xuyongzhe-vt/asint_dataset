import json
from collections import defaultdict
from pathlib import Path

ASINT_DIR = Path(__file__).resolve().parent.parent / "2025-09"

def load_asint_dataset(asint_dir: Path = ASINT_DIR):
    with open(asint_dir / "saint.org_families.json", encoding="utf-8") as f:
        records = json.load(f)

    fam_to_asns = defaultdict(set)
    asn_to_name = {}
    for g in records:
        fid = g["org_family_id"]
        for e in g.get("asn_entries", []) or []:
            asn = e.get("asn")
            name = e.get("org_name")
            if asn is None:
                continue
            asn = int(asn)
            fam_to_asns[fid].add(asn)
            if name:
                asn_to_name[asn] = name

    family_asn_lists = [sorted(s) for s in fam_to_asns.values() if s]
    return family_asn_lists, asn_to_name

if __name__ == "__main__":
    families, asn_to_name = load_asint_dataset()
    total_asns = sum(len(f) for f in families)
    print(f"Families: {len(families)}")
    print(f"Total ASN occurrences: {total_asns}")
    print(f"Unique ASNs with org_name mapping: {len(asn_to_name)}")
