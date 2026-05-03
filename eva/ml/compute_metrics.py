"""Reproduce final_table.csv from per-model predictions and the benchmark gold labels."""
import csv
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
BENCH = ROOT / 'benchmark_pairs.jsonl'
MODELS_DIR = ROOT / 'models'
OUT = ROOT / 'final_table.csv'

POS = {'alias', 'A_parent_B', 'B_parent_A'}

# (model_dir_name, display_name, concurrency_used_at_eval_time)
MODELS = [
    ('qwen2_5_72b',                   'Qwen2.5-72B',                 2),
    ('deepseek_r1_distill_llama_70b', 'DS-R1-Distill-Llama-70B',     2),
    ('deepseek_r1_distill_32b',       'DS-R1-Distill-Qwen-32B',      8),
    ('qwen2_5_32b',                   'Qwen2.5-32B',                 8),
    ('gpt_oss_20b',                   'gpt-oss-20b',                 4),
    ('deepseek_r1_distill_qwen_7b',   'DS-R1-Distill-Qwen-7B',      40),
    ('qwen2_5_7b',                    'Qwen2.5-7B',                 30),
    ('qwen2_5_3b',                    'Qwen2.5-3B',                 50),
    ('qwen2_5_0_5b',                  'Qwen2.5-0.5B',              100),
    ('ablation_no_context',           'DS-32B (no context)',         8),
    ('ablation_minimal_prompt',       'DS-32B (minimal prompt)',     8),
]


def score(pred_path, gold):
    tp = fp = fn = tn = loops = 0
    lats, outs = [], []
    n = 0
    with open(pred_path) as f:
        for line in f:
            r = json.loads(line)
            n += 1
            g_label = gold[r['pair_id']]['gold_label']
            pred = r.get('prediction')
            pos_gold = g_label in POS
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
            if r.get('latency_ms') is not None:
                lats.append(r['latency_ms'])
            if r.get('output_tokens') is not None:
                outs.append(r['output_tokens'])
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    n_valid = n - loops
    acc = (tp + tn) / n_valid if n_valid else 0.0
    return {
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'loops': loops, 'n_total': n,
        'failure_rate': loops / n if n else 0.0,
        'P': prec, 'R': rec, 'F1': f1, 'Acc': acc,
        'avg_lat_s': mean(lats) / 1000 if lats else None,
        'avg_out_tok': mean(outs) if outs else None,
    }


def main():
    gold = {json.loads(l)['pair_id']: json.loads(l) for l in open(BENCH)}
    n_pos = sum(1 for g in gold.values() if g['gold_label'] in POS)
    print(f'Benchmark: n={len(gold)} (pos={n_pos}, neg={len(gold) - n_pos})')
    print()

    rows = []
    for key, display, conc in MODELS:
        pred_path = MODELS_DIR / key / 'predictions.jsonl'
        if not pred_path.exists():
            print(f'MISSING: {pred_path}')
            continue
        m = score(pred_path, gold)
        pps = conc / m['avg_lat_s'] if m['avg_lat_s'] else None
        rows.append((display, conc, m, pps))

    print(f'{"Model":<28} {"Conc":>5} {"Fail%":>6} {"Loops":>5}  '
          f'{"P":>6} {"R":>6} {"F1":>6}  {"Lat(s)":>7} {"P/s":>6}')
    print('-' * 90)
    for display, conc, m, pps in rows:
        lat = f'{m["avg_lat_s"]:>6.1f}s' if m['avg_lat_s'] is not None else '     --'
        pps_s = f'{pps:>5.2f}' if pps is not None else '   --'
        print(f'{display:<28} {conc:>5} {m["failure_rate"] * 100:>5.1f}% {m["loops"]:>5}  '
              f'{m["P"] * 100:>5.1f}% {m["R"] * 100:>5.1f}% {m["F1"] * 100:>5.1f}%  '
              f'{lat} {pps_s}')

    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['model', 'concurrency', 'failure_rate_pct', 'loops', 'n_total',
                    'P_pct', 'R_pct', 'F1_pct', 'Acc_pct',
                    'avg_latency_s', 'pairs_per_sec_system', 'avg_out_tokens',
                    'TP', 'FP', 'FN', 'TN'])
        for display, conc, m, pps in rows:
            w.writerow([
                display, conc,
                f'{m["failure_rate"] * 100:.2f}', m['loops'], m['n_total'],
                f'{m["P"] * 100:.2f}', f'{m["R"] * 100:.2f}',
                f'{m["F1"] * 100:.2f}', f'{m["Acc"] * 100:.2f}',
                f'{m["avg_lat_s"]:.2f}' if m['avg_lat_s'] is not None else '',
                f'{pps:.2f}' if pps is not None else '',
                f'{m["avg_out_tok"]:.0f}' if m['avg_out_tok'] is not None else '',
                m['tp'], m['fp'], m['fn'], m['tn'],
            ])
    print(f'\nWrote {OUT}')


if __name__ == '__main__':
    main()
