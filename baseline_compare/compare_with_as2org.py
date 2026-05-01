import json
from pathlib import Path
from asint_loader import load_asint_dataset
from compare import compare_dataset
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE_FILE = ROOT / 'baseline-2025-09' / 'as2org.jsonl'
OUTPUT_DIR = HERE / 'as2org'

def load_candidate():
    orgid_to_asns = {}
    with open(CANDIDATE_FILE, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('type') == 'ASN':
                orgid_to_asns.setdefault(entry['organizationId'], []).append(entry['asn'])
    return list(orgid_to_asns.values())

def main():
    asint_families, asn_to_name = load_asint_dataset()
    candidate_families = load_candidate()
    compare_dataset(asint_families, candidate_families, asn_to_name, str(OUTPUT_DIR))
    print(f'Wrote comparison to {OUTPUT_DIR}')
if __name__ == '__main__':
    main()
