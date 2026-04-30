import json
from pathlib import Path

from asint_loader import load_asint_dataset
from compare import compare_dataset

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE_FILE = ROOT / "baseline-2025-09" / "as2org+.json"
OUTPUT_DIR = HERE / "as2org+"

def load_candidate():
    with open(CANDIDATE_FILE, encoding="utf-8") as f:
        return json.load(f)

def main():
    asint_families, asn_to_name = load_asint_dataset()
    candidate_families = load_candidate()
    compare_dataset(asint_families, candidate_families, asn_to_name, str(OUTPUT_DIR))
    print(f"Wrote comparison to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
