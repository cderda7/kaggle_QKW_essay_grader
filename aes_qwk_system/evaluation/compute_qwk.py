#!/usr/bin/env python3
"""
compute_qwk.py — evaluation script for the AES QWK grading system (v1).

Loads grading/predictions_v1.csv and computes:
  - QWK (quadratic weighted kappa) between human_score and system_holistic_score
  - Confusion matrix
  - Exact-agreement and adjacent (+/-1) agreement rates
  - Mean signed error and MAE
  - Verbosity-bias diagnostics: corr(word_count, human_score), corr(word_count, system_score),
    corr(word_count, residual) where residual = system_score - human_score

Writes results_v1.json (machine-readable) and prints a human-readable summary.
Run: python3 compute_qwk.py
"""

import csv
import json
import os
import statistics

from sklearn.metrics import cohen_kappa_score, confusion_matrix

HERE = os.path.dirname(os.path.abspath(__file__))
PREDICTIONS_FILE = os.path.join(HERE, "..", "grading", "predictions_v1.csv")
RESULTS_JSON = os.path.join(HERE, "results_v1.json")


def pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def main():
    rows = []
    with open(PREDICTIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "essay_id": row["essay_id"],
                "human": int(row["human_score"]),
                "system": int(row["system_holistic_score"]),
                "org": int(row["system_organization"]),
                "dev": int(row["system_development"]),
                "conv": int(row["system_conventions"]),
                "words": int(row["word_count"]),
            })

    human = [r["human"] for r in rows]
    system = [r["system"] for r in rows]
    words = [r["words"] for r in rows]
    residual = [s - h for s, h in zip(system, human)]

    n = len(rows)
    all_labels = sorted(set(human) | set(system))

    qwk = cohen_kappa_score(human, system, weights="quadratic", labels=all_labels)
    cm = confusion_matrix(human, system, labels=all_labels).tolist()

    exact = sum(1 for h, s in zip(human, system) if h == s) / n
    adjacent = sum(1 for h, s in zip(human, system) if abs(h - s) <= 1) / n
    mae = sum(abs(h - s) for h, s in zip(human, system)) / n
    mean_signed_error = sum(residual) / n

    corr_words_human = pearson(words, human)
    corr_words_system = pearson(words, system)
    corr_words_residual = pearson(words, residual)

    results = {
        "n_essays": n,
        "labels": all_labels,
        "qwk": qwk,
        "confusion_matrix": {"labels": all_labels, "matrix": cm,
                              "note": "rows=human_score, cols=system_score"},
        "exact_agreement_rate": exact,
        "adjacent_agreement_rate_within_1": adjacent,
        "mean_absolute_error": mae,
        "mean_signed_error_system_minus_human": mean_signed_error,
        "verbosity_bias_diagnostics": {
            "corr_word_count_human_score": corr_words_human,
            "corr_word_count_system_score": corr_words_system,
            "corr_word_count_residual": corr_words_residual,
            "human_baseline_note": "0.688 measured independently on this same 100-row file "
                                    "during data recon before grading",
        },
    }

    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2)

    print(f"n_essays: {n}")
    print(f"labels present: {all_labels}")
    print(f"QWK: {qwk:.4f}")
    print(f"Exact agreement: {exact:.1%}")
    print(f"Adjacent (+/-1) agreement: {adjacent:.1%}")
    print(f"MAE: {mae:.3f}")
    print(f"Mean signed error (system - human): {mean_signed_error:+.3f}")
    print(f"corr(word_count, human_score): {corr_words_human:.3f}")
    print(f"corr(word_count, system_score): {corr_words_system:.3f}")
    print(f"corr(word_count, residual): {corr_words_residual:.3f}")
    print()
    print("Confusion matrix (rows=human, cols=system), labels=", all_labels)
    for label, row in zip(all_labels, cm):
        print(f"  human={label}: {row}")
    print()
    print(f"Wrote {RESULTS_JSON}")


if __name__ == "__main__":
    main()
