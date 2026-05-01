import csv
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
BENCH = ROOT / 'benchmark' / 'benchmark_pairs.jsonl'
PRED_DIR = ROOT / 'benchmark' / 'predictions'
OUT_DIR = ROOT / 'benchmark' / 'results'
POS = {'alias', 'B_parent_A', 'A_parent_B'}
MODEL_ORDER = [('deepseek_r1_distill_32b', 'DeepSeek-R1-Distill-32B', 8), ('qwen25_72b', 'Qwen2.5-72B', 2), ('qwen25_32b', 'Qwen2.5-32B', 8), ('gpt_oss_20b', 'gpt-oss-20b', 4), ('qwen25_7b', 'Qwen2.5-7B', 30), ('qwen25_3b', 'Qwen2.5-3B', 50), ('qwen25_1_5b', 'Qwen2.5-1.5B', 40), ('qwen25_0_5b', 'Qwen2.5-0.5B', 100), ('deepseek_ablation_no_context', 'DS-32B (no context)', 8), ('deepseek_ablation_minimal_prompt', 'DS-32B (minimal prompt)', 8)]

def score(preds, gold):
    from statistics import mean
    tp = fp = fn = tn = loops = 0
    n_total = len(gold)
    lats, outs = ([], [])
    for pid, g in gold.items():
        rec = preds.get(pid, {})
        pred = rec.get('prediction')
        pos_gold = g['gold_label'] in POS
        if pred is None:
            loops += 1
            continue
        pos_pred = pred in POS
        if pos_gold and pos_pred:
            tp += 1
        elif pos_gold:
            fn += 1
        elif pos_pred:
            fp += 1
        else:
            tn += 1
        if rec.get('latency_ms') is not None:
            lats.append(rec['latency_ms'])
        if rec.get('output_tokens') is not None:
            outs.append(rec['output_tokens'])
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    n_valid = n_total - loops
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, loops=loops, n_total=n_total, n_valid=n_valid, failure_rate=loops / n_total, precision=p, recall=r, f1=f1, accuracy=(tp + tn) / n_valid if n_valid else 0.0, avg_latency_s=mean(lats) / 1000 if lats else None, avg_out_tok=mean(outs) if outs else None)

def main():
    gold = {json.loads(l)['pair_id']: json.loads(l) for l in open(BENCH)}
    avail = {p.stem.removeprefix('predictions_'): p for p in PRED_DIR.glob('predictions_*.jsonl')}
    rows = []
    for key, display, conc in MODEL_ORDER:
        if key not in avail:
            continue
        preds = {json.loads(l)['pair_id']: json.loads(l) for l in open(avail[key])}
        m = score(preds, gold)
        m['conc'] = conc
        m['system_throughput'] = conc / m['avg_latency_s'] if m['avg_latency_s'] else None
        rows.append((display, m))
    md = ['# Final results — loops excluded from P/R/F1, reported as failure rate', '', f'Benchmark: n={len(gold)} (pos={sum((1 for g in gold.values() if g['gold_label'] in POS))}, neg={sum((1 for g in gold.values() if g['gold_label'] not in POS))})', '', '| Model | Conc | Failure rate | P | R | F1 | Acc | Pairs/s |', '|---|---|---|---|---|---|---|---|']
    for d, m in rows:
        tp = f'{m['system_throughput']:.2f}' if m['system_throughput'] else '—'
        md.append(f'| **{d}** | {m['conc']} | {m['failure_rate'] * 100:.1f}% ({m['loops']}/{m['n_total']}) | {m['precision'] * 100:.1f}% | {m['recall'] * 100:.1f}% | {m['f1'] * 100:.1f}% | {m['accuracy'] * 100:.1f}% | **{tp}** |')
    (OUT_DIR / 'final_table.md').write_text('\n'.join(md) + '\n')
    with open(OUT_DIR / 'final_table.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['model', 'concurrency', 'failure_rate_pct', 'loops', 'n_total', 'P_pct', 'R_pct', 'F1_pct', 'Acc_pct', 'avg_latency_s', 'pairs_per_sec_system', 'avg_out_tokens', 'TP', 'FP', 'FN', 'TN'])
        for d, m in rows:
            w.writerow([d, m['conc'], f'{m['failure_rate'] * 100:.2f}', m['loops'], m['n_total'], f'{m['precision'] * 100:.2f}', f'{m['recall'] * 100:.2f}', f'{m['f1'] * 100:.2f}', f'{m['accuracy'] * 100:.2f}', f'{m['avg_latency_s']:.2f}' if m['avg_latency_s'] is not None else '', f'{m['system_throughput']:.2f}' if m['system_throughput'] is not None else '', f'{m['avg_out_tok']:.0f}' if m['avg_out_tok'] is not None else '', m['tp'], m['fp'], m['fn'], m['tn']])
    print('\n'.join(md))
    print(f'\nWrote final_table.md + .csv')
if __name__ == '__main__':
    main()
