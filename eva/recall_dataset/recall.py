import json
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GT_PATH = HERE / 'recall_gt_final.json'
ASINT_PATH = ROOT / '2025-09' / 'saint.org_families.json'
CAIDA_PATH = ROOT / 'baseline-2025-09' / 'as2org.jsonl'
ASORGPLUS_PATH = ROOT / 'baseline-2025-09' / 'as2org+.json'
SIBLING_PATH = ROOT / 'baseline-2025-09' / 'as_sibling.json'
BORGES_PATH = ROOT / 'baseline-2025-09' / 'borges.json'

def load_gt():
    with open(GT_PATH) as f:
        d = json.load(f)
    out = {}
    for org, v in d.items():
        if isinstance(v, dict):
            asns = v.get('asns') or v.get('ASNs') or []
        else:
            asns = v
        out[org] = set((int(a) for a in asns))
    return out

def load_asint():
    with open(ASINT_PATH) as f:
        records = json.load(f)
    fam_to_asns = defaultdict(set)
    for r in records:
        fid = r['org_family_id']
        for e in r.get('asn_entries') or []:
            a = e.get('asn')
            if a is not None:
                fam_to_asns[fid].add(int(a))
    return list(fam_to_asns.values())

def load_caida():
    out = defaultdict(set)
    with open(CAIDA_PATH) as f:
        for line in f:
            e = json.loads(line)
            if e.get('type') == 'ASN':
                out[e['organizationId']].add(int(e['asn']))
    return list(out.values())

def load_asorgplus():
    with open(ASORGPLUS_PATH) as f:
        clusters = json.load(f)
    return [set((int(a) for a in c)) for c in clusters]

def load_sibling():
    with open(SIBLING_PATH) as f:
        d = json.load(f)
    records = d.get('data', d)
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = (find(a), find(b))
        if ra != rb:
            parent[rb] = ra
    for k, ent in records.items():
        try:
            kk = int(k)
        except (TypeError, ValueError):
            continue
        parent.setdefault(kk, kk)
        for s in ent.get('Sibling ASNs', []) or []:
            try:
                aa = int(s)
            except (TypeError, ValueError):
                continue
            parent.setdefault(aa, aa)
            union(kk, aa)
    cl = defaultdict(set)
    for a in parent:
        cl[find(a)].add(a)
    return list(cl.values())

def load_borges():
    with open(BORGES_PATH) as f:
        d = json.load(f)
    g = defaultdict(set)
    for ent in d:
        a = ent.get('asn')
        if a is not None:
            g[ent['group_id']].add(int(a))
    asn_to_g = defaultdict(list)
    for gid, asns in g.items():
        for a in asns:
            asn_to_g[a].append(gid)
    for a, gids in asn_to_g.items():
        if len(gids) > 1:
            keep = max(gids, key=lambda gg: len(g[gg]))
            for gg in gids:
                if gg != keep:
                    g[gg].discard(a)
    return [v for v in g.values() if v]

def compute_recall(gt, clusters):
    asn_to_cluster = {}
    for ci, cl in enumerate(clusters):
        for a in cl:
            asn_to_cluster[a] = ci
    rows = []
    for org, gt_asns in gt.items():
        cluster_overlap = defaultdict(int)
        for a in gt_asns:
            ci = asn_to_cluster.get(a)
            if ci is not None:
                cluster_overlap[ci] += 1
        if not cluster_overlap:
            rows.append((org, len(gt_asns), len(gt_asns), 0, 0.0))
            continue
        best_ci, best_overlap = max(cluster_overlap.items(), key=lambda kv: kv[1])
        recall = best_overlap / len(gt_asns)
        rows.append((org, len(gt_asns), len(gt_asns), best_overlap, recall))
    return rows

def main():
    gt = load_gt()
    datasets = {'ASINT': load_asint(), 'CAIDA': load_caida(), 'AS2Org+': load_asorgplus(), 'Sibling': load_sibling(), 'Borges': load_borges()}
    all_rows = {name: compute_recall(gt, cs) for name, cs in datasets.items()}
    name_order = ['ASINT', 'CAIDA', 'AS2Org+', 'Sibling', 'Borges']
    lines = []
    lines.append(f'Ground-truth orgs: {len(gt)}; total GT ASNs: {sum((len(v) for v in gt.values()))}')
    lines.append('')
    lines.append('Per-org recall (best-matching cluster / common ASNs in dataset)')
    header = ['Org', 'GT'] + name_order
    lines.append('  '.join((f'{h:>16}' for h in header)))
    lines.append('-' * (18 * len(header)))
    for org in gt:
        cells = [f'{org[:16]:>16}', f'{len(gt[org]):>16}']
        for name in name_order:
            r = next((row for row in all_rows[name] if row[0] == org))
            cells.append(f'{r[4] * 100:>10.2f}% ({r[2]:>3})')
        lines.append('  '.join(cells))
    lines.append('')
    lines.append(f'{'Dataset':>10}  {'Macro recall':>14}  {'Micro recall':>14}')
    lines.append('-' * 44)
    for name in name_order:
        rows = all_rows[name]
        macro = sum((r[4] for r in rows)) / len(rows)
        total_common = sum((r[2] for r in rows))
        total_best = sum((r[3] for r in rows))
        micro = total_best / total_common if total_common else 0.0
        lines.append(f'{name:>10}  {macro * 100:>13.2f}%  {micro * 100:>13.2f}%')
    text = '\n'.join(lines) + '\n'
    print(text, end='')
    out = HERE / 'recall_results.txt'
    out.write_text(text, encoding='utf-8')
    print(f'\nWrote {out}')
if __name__ == '__main__':
    main()
