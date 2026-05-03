import json
import re
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MONTHS = ['2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02']
PAIRS = list(zip(MONTHS, MONTHS[1:]))
_ws = re.compile('\\s+')

def norm(s):
    return _ws.sub(' ', s.strip()).casefold()

def load_snapshot(month):
    path = ROOT / month / 'saint.org_families.json'
    with open(path) as f:
        records = json.load(f)
    fam_orgs = defaultdict(set)
    for r in records:
        fid = r.get('org_family_id')
        if fid is None:
            continue
        for e in r.get('asn_entries') or []:
            on = e.get('org_name')
            if isinstance(on, str) and on.strip():
                fam_orgs[fid].add(norm(on))
    return fam_orgs

def signatures(fam_orgs, common):
    sigs = {}
    for fid, orgs in fam_orgs.items():
        f = orgs & common
        if f:
            sigs.setdefault(frozenset(f), set()).add(fid)
    return sigs

def analyze(snap_a, snap_b):
    fam_a = load_snapshot(snap_a)
    fam_b = load_snapshot(snap_b)
    orgs_a = set().union(*fam_a.values())
    orgs_b = set().union(*fam_b.values())
    common = orgs_a & orgs_b
    sig_a = signatures(fam_a, common)
    sig_b = signatures(fam_b, common)
    set_a = set(sig_a.keys())
    set_b = set(sig_b.keys())
    identical = set_a & set_b
    union = set_a | set_b
    jaccard = len(identical) / len(union) if union else 0.0
    unique_a = set_a - identical
    unique_b = set_b - identical
    a_to_b = {}
    for sa in unique_a:
        for sb in unique_b:
            if sa < sb:
                a_to_b.setdefault(sa, []).append(sb)
                break
    b_to_a = {}
    for sb in unique_b:
        for sa in unique_a:
            if sb < sa:
                b_to_a.setdefault(sb, []).append(sa)
                break
    enr_orgs = sum((len(sa) for sa in a_to_b))
    ref_orgs = sum((len(sb) for sb in b_to_a))
    changed_orgs = set()
    for s in unique_a:
        changed_orgs |= s
    for s in unique_b:
        changed_orgs |= s
    changed = len(changed_orgs)
    return {'common_orgs': len(common), 'fams_a': len(set_a), 'fams_b': len(set_b), 'identical': len(identical), 'jaccard_pct': jaccard * 100, 'unique_a': len(unique_a), 'unique_b': len(unique_b), 'a_subsumed_by_b': len(a_to_b), 'b_subsumed_by_a': len(b_to_a), 'enr_orgs': enr_orgs, 'ref_orgs': ref_orgs, 'changed_orgs': changed}

def main():
    lines = []
    lines.append(f"{'Pair':>20} {'common_orgs':>13} {'fams_A':>8} {'fams_B':>8} {'identical':>10} {'Jaccard':>9}")
    lines.append('-' * 75)
    rows = []
    for a, b in PAIRS:
        r = analyze(a, b)
        rows.append((a, b, r))
        pair_label = f'{a} -> {b}'
        lines.append(f"{pair_label:>20} {r['common_orgs']:>13,} {r['fams_a']:>8,} {r['fams_b']:>8,} {r['identical']:>10,} {r['jaccard_pct']:>8.2f}%")
    lines.append('')
    lines.append('Per-pair detail (changes):')
    lines.append(f"{'Pair':>20} {'changed':>9} {'changed%':>9}  {'enr':>7} {'enr%':>6}  {'ref':>7} {'ref%':>6}")
    lines.append('-' * 80)
    for a, b, r in rows:
        chg = r['changed_orgs']
        enr = r['enr_orgs']
        ref = chg - enr
        chg_pct = chg / r['common_orgs'] * 100 if r['common_orgs'] else 0
        enr_pct = enr / chg * 100 if chg else 0
        ref_pct = ref / chg * 100 if chg else 0
        pair_label = f'{a} -> {b}'
        lines.append(f"{pair_label:>20} {chg:>9,} {chg_pct:>8.2f}%  {enr:>7,} {enr_pct:>5.1f}%  {ref:>7,} {ref_pct:>5.1f}%")
    text = '\n'.join(lines) + '\n'
    print(text, end='')
    out = HERE / 'longitudinal_results.txt'
    out.write_text(text, encoding='utf-8')
    print(f'\nWrote {out}')
if __name__ == '__main__':
    main()
