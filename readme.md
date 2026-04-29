# §8.2 Organization-Level Eyeball Ranking

Analysis for the IMC 2026 paper: how ASINT's family merges reshape the
ranking of eyeball ISPs (directly addresses reviewer 30D's "cone-size-only"
concern).

## Pipeline (planned)

1. **`data/`** — inputs
   - `apnic_aspop.csv` — APNIC stats.labs.apnic.net/aspop per-ASN eyeball
     share (to be downloaded, ideally dated near 2025-09)
   - ASINT snapshot (from `../asint/saint.org_families.json` or
     `/home/yongzhe/as2org_llm/longitivy_analyse/2025-09.json`)
   - CAIDA baseline (from `../as2org/20250701.as-org2info.jsonl`)

2. **`scripts/`** — analysis
   - `coverage_check.py` — overlap ASN counts between APNIC / ASINT / CAIDA
   - `org_ranking.py`   — top-N org eyeball share under each mapping
   - `concentration.py` — top-10/20/50 cumulative share, HHI
   - `case_study.py`    — find named ISPs with biggest rank jump

3. **`results/`** — outputs
   - `coverage.csv`
   - `top_orgs_asint_vs_baseline.csv`
   - `concentration.csv`
   - `case_studies.md`

## Decisions still needed

- **Snapshot alignment**: paper §8.1 uses 2026-01; reviewer data may require
  2025-09 to match APNIC publication date. Prefer one:
  - 2025-09 ASINT (from `longitivy_analyse/2025-09.json`, 82,527 families)
  - 2026-01 ASINT (from `../asint/saint.org_families.json`, 82,527 families)
- **APNIC data source**: CSV download URL? Version/date?
- **Baseline**: CAIDA `20250701.as-org2info.jsonl` (what we have) or a more
  recent one?
