\
\
\
\
\
\
\
\
\
\
\
   
import csv
import json
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent.parent
BENCH = ROOT / "benchmark" / "benchmark_pairs.jsonl"
PRED_DIR = ROOT / "benchmark" / "predictions"
OUT_DIR = ROOT / "benchmark" / "results"

                                                                         
MODEL_ORDER = [
    ("qwen25_72b", "Qwen2.5-72B"),
    ("deepseek_r1_distill_32b", "DeepSeek-R1-Distill-Qwen-32B"),
    ("qwen25_32b", "Qwen2.5-32B"),
    ("gpt_oss_20b", "gpt-oss-20b"),
    ("qwen25_7b", "Qwen2.5-7B"),
    ("qwen25_3b", "Qwen2.5-3B"),
    ("qwen25_1_5b", "Qwen2.5-1.5B"),
    ("qwen25_0_5b", "Qwen2.5-0.5B"),
    ("deepseek_ablation_no_context", "DS-32B (no context)"),
    ("deepseek_ablation_minimal_prompt", "DS-32B (minimal prompt)"),
]

POS_PRED = {"alias", "B_parent_A", "A_parent_B"}
POS_GOLD = {"alias", "B_parent_A", "A_parent_B"}

def metrics(preds, gold):
    tp = fp = fn = tn = loops = 0
    lats, outs = [], []
    for pid, g in gold.items():
        p = preds.get(pid, {})
        pred = p.get("prediction")
        pos_gold = g["gold_label"] in POS_GOLD
        if pred is None:
            loops += 1
            if pos_gold:
                fn += 1
            else:
                tn += 1
        else:
            pos_pred = pred in POS_PRED
            if pos_gold and pos_pred:
                tp += 1
            elif pos_gold and not pos_pred:
                fn += 1
            elif not pos_gold and pos_pred:
                fp += 1
            else:
                tn += 1
        if p.get("latency_ms") is not None:
            lats.append(p["latency_ms"])
        if p.get("output_tokens") is not None:
            outs.append(p["output_tokens"])

    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    acc = (tp + tn) / n if n else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "loops": loops,
        "precision": prec, "recall": rec, "specificity": spec,
        "f1": f1, "accuracy": acc,
        "avg_latency_s": mean(lats) / 1000 if lats else None,
        "p50_latency_s": median(lats) / 1000 if lats else None,
        "avg_output_tokens": mean(outs) if outs else None,
    }

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold = {json.loads(l)["pair_id"]: json.loads(l) for l in open(BENCH)}
    n_pos = sum(1 for g in gold.values() if g["gold_label"] in POS_GOLD)
    n_neg = len(gold) - n_pos
    print(f"Benchmark: n={len(gold)} (pos={n_pos}, neg={n_neg})")

                                
    available = {p.stem.removeprefix("predictions_"): p for p in PRED_DIR.glob("predictions_*.jsonl")}

    rows = []
    for key, display in MODEL_ORDER:
        if key not in available:
            print(f"  skip {display} (no predictions)")
            continue
        preds = {json.loads(l)["pair_id"]: json.loads(l) for l in open(available[key])}
        m = metrics(preds, gold)
        rows.append({"key": key, "model": display, **m})

                 
    csv_path = OUT_DIR / "main_table.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "TP", "FP", "FN", "TN", "loops",
            "precision", "recall", "specificity", "F1", "accuracy",
            "avg_latency_s", "p50_latency_s", "avg_output_tokens",
        ])
        for r in rows:
            w.writerow([
                r["model"], r["tp"], r["fp"], r["fn"], r["tn"], r["loops"],
                f"{r['precision']*100:.2f}%", f"{r['recall']*100:.2f}%",
                f"{r['specificity']*100:.2f}%", f"{r['f1']*100:.2f}%", f"{r['accuracy']*100:.2f}%",
                f"{r['avg_latency_s']:.2f}" if r["avg_latency_s"] is not None else "",
                f"{r['p50_latency_s']:.2f}" if r["p50_latency_s"] is not None else "",
                f"{r['avg_output_tokens']:.0f}" if r["avg_output_tokens"] is not None else "",
            ])

                      
    md_lines = [
        "| Model | P | R | Spec | F1 | Acc | Loops | Avg Lat | Avg Out Tok |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        md_lines.append(
            f"| **{r['model']}** | {r['precision']*100:.1f}% | {r['recall']*100:.1f}% | "
            f"{r['specificity']*100:.1f}% | {r['f1']*100:.1f}% | {r['accuracy']*100:.1f}% | "
            f"{r['loops']} | "
            f"{r['avg_latency_s']:.1f}s | "
            f"{r['avg_output_tokens']:.0f}"
            " |"
        )
    (OUT_DIR / "main_table.md").write_text("\n".join(md_lines) + "\n")

                              
    tex_lines = [
        r"\begin{table}[t]",
        r"\caption{Stage-D pairwise validator performance across LLMs on the 300-pair human-verified benchmark (150 positive + 150 negative).}",
        r"\label{tab:llm_ablation}",
        r"\centering\small",
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"Model & P & R & Spec. & F1 & Acc. & Loops & Lat. (s) & Out. tok. \\",
        r"\midrule",
    ]
    for r in rows:
        tex_lines.append(
            f"{r['model']} & "
            f"{r['precision']*100:.1f} & {r['recall']*100:.1f} & "
            f"{r['specificity']*100:.1f} & {r['f1']*100:.1f} & {r['accuracy']*100:.1f} & "
            f"{r['loops']} & "
            f"{r['avg_latency_s']:.1f} & "
            f"{r['avg_output_tokens']:.0f} \\\\"
        )
    tex_lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (OUT_DIR / "main_table.tex").write_text("\n".join(tex_lines) + "\n")

    print(f"\nWrote {csv_path.name}, main_table.md, main_table.tex to {OUT_DIR}")
    for r in rows:
        print(f"  {r['model']:<34} P={r['precision']*100:5.1f}  R={r['recall']*100:5.1f}  F1={r['f1']*100:5.1f}  Loops={r['loops']}")

if __name__ == "__main__":
    main()
