import json
from collections import defaultdict
from pathlib import Path
from asint_loader import load_asint_dataset
from compare import compare_dataset
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE_FILE = ROOT / 'baseline-2025-09' / 'borges.json'
OUTPUT_DIR = HERE / 'borges'

def load_candidate():
    with open(CANDIDATE_FILE, encoding='utf-8') as f:
        group_data = json.load(f)
    groupid_to_asns = defaultdict(set)
    for entry in group_data:
        asn = entry.get('asn')
        if asn is not None:
            groupid_to_asns[entry['group_id']].add(asn)
    asn_to_groups = defaultdict(list)
    for gid, asns in groupid_to_asns.items():
        for a in asns:
            asn_to_groups[a].append(gid)
    for a, gids in asn_to_groups.items():
        if len(gids) > 1:
            keep = max(gids, key=lambda g: len(groupid_to_asns[g]))
            for g in gids:
                if g != keep:
                    groupid_to_asns[g].discard(a)
    return [list(asns) for asns in groupid_to_asns.values() if asns]

def main():
    asint_families, asn_to_name = load_asint_dataset()
    candidate_families = load_candidate()
    compare_dataset(asint_families, candidate_families, asn_to_name, str(OUTPUT_DIR))
    print(f'Wrote comparison to {OUTPUT_DIR}')
if __name__ == '__main__':
    main()
