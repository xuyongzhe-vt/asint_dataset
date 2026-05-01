import csv
import json
from pathlib import Path
from statistics import mean
ROOT = Path(__file__).resolve().parent.parent.parent
BENCH = ROOT / 'benchmark' / 'benchmark_pairs.jsonl'
ARCHIVE = ROOT / 'benchmark' / 'archive' / 'final_snapshot_20260420' / 'predictions'
V2 = ROOT / 'llm_eval_v2' / 'predictions'
OUT = ROOT / 'llm_eval_v2' / 'results' / 'final_table_v2.csv'
POS = {'alias', 'B_parent_A', 'A_parent_B'}
ROWS = [('Qwen2.5-72B', ARCHIVE / 'predictions_qwen25_72b.jsonl', 2), ('DS-R1-Distill-Llama-70B', V2 / 'predictions_deepseek_r1_distill_llama_70b.jsonl', 2), ('DS-R1-Distill-Qwen-32B', ARCHIVE / 'predictions_deepseek_r1_distill_32b.jsonl', 8), ('Qwen2.5-32B', ARCHIVE / 'predictions_qwen25_32b.jsonl', 8), ('gpt-oss-20b', ARCHIVE / 'predictions_gpt_oss_20b.jsonl', 4), ('DS-R1-Distill-Qwen-7B', V2 / 'predictions_deepseek_r1_distill_qwen_7b.jsonl', 40), ('Qwen2.5-7B', ARCHIVE / 'predictions_qwen25_7b.jsonl', 30), ('Qwen2.5-3B', ARCHIVE / 'predictions_qwen25_3b.jsonl', 50), ('Qwen2.5-0.5B', ARCHIVE / 'predictions_qwen25_0_5b.jsonl', 100), ('DS-32B (no context)', ARCHIVE / 'predictions_deepseek_ablation_no_context.jsonl', 8), ('DS-32B (minimal prompt)', ARCHIVE / 'predictions_deepseek_ablation_minimal_prompt.jsonl', 8)]

def score(path, gold):
    tp = fp = fn = tn = loops = 0
    lats = []
    outs = []
    recs = [json.loads(l) for l in open(path)]
    for r in recs:
        pid = r['pair_id']
        g = gold[pid]['gold_label']
        p = r.get('prediction')
        pg = g in POS
        if p is None:
            loops += 1
            continue
        pp = p in POS
        if pg and pp:
            tp += 1
        elif pg:
            fn += 1
        elif pp:
            fp += 1
        else:
            tn += 1
        if r.get('latency_ms') is not None:
            lats.append(r['latency_ms'])
        if r.get('output_tokens') is not None:
            outs.append(r['output_tokens'])
    n = len(recs)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    n_valid = n - loops
    acc = (tp + tn) / n_valid if n_valid else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'loops': loops, 'n_total': n, 'failure_rate': loops / n if n else 0.0, 'P': prec, 'R': rec, 'F1': f1, 'Acc': acc, 'avg_lat_s': mean(lats) / 1000 if lats else None, 'avg_out_tok': mean(outs) if outs else None}

def main():
    gold = {json.loads(l)['pair_id']: json.loads(l) for l in open(BENCH)}
    n_pos = sum((1 for g in gold.values() if g['gold_label'] in POS))
    print(f'Benchmark: n={len(gold)} (pos={n_pos}, neg={len(gold) - n_pos})')
    print()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['model', 'concurrency', 'failure_rate_pct', 'loops', 'n_total', 'P_pct', 'R_pct', 'F1_pct', 'Acc_pct', 'avg_latency_s', 'pairs_per_sec_system', 'avg_out_tokens', 'TP', 'FP', 'FN', 'TN'])
        print(f'{'Model':<28} {'Conc':>5} {'Fail%':>6} {'Loops':>5}  {'P':>6} {'R':>6} {'F1':>6}  {'Lat(s)':>7} {'P/s':>6} {'Tok':>5}')
        print('-' * 100)
        for name, path, conc in ROWS:
            if not path.exists():
                print(f'MISSING: {path}')
                continue
            m = score(path, gold)
            pps = conc / m['avg_lat_s'] if m['avg_lat_s'] else None
            print(f'{name:<28} {conc:>5} {m['failure_rate'] * 100:>5.1f}% {m['loops']:>5}  {m['P'] * 100:>5.1f}% {m['R'] * 100:>5.1f}% {m['F1'] * 100:>5.1f}%  {m['avg_lat_s']:>6.1f}s {pps:>5.2f} {(int(m['avg_out_tok']) if m['avg_out_tok'] else '—'):>5}')
            w.writerow([name, conc, f'{m['failure_rate'] * 100:.2f}', m['loops'], m['n_total'], f'{m['P'] * 100:.2f}', f'{m['R'] * 100:.2f}', f'{m['F1'] * 100:.2f}', f'{m['Acc'] * 100:.2f}', f'{m['avg_lat_s']:.2f}' if m['avg_lat_s'] else '', f'{pps:.2f}' if pps else '', f'{m['avg_out_tok']:.0f}' if m['avg_out_tok'] else '', m['tp'], m['fp'], m['fn'], m['tn']])
    print(f'\nWrote {OUT}')
if __name__ == '__main__':
    main()
