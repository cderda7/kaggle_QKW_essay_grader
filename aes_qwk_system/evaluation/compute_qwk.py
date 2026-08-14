#!/usr/bin/env python3
"""
compute_qwk.py — evaluation script for the AES QWK grading system.

Loads grading/predictions_<version>.csv and computes:
  - QWK (quadratic weighted kappa) between human_score and system_holistic_score
  - Confusion matrix
  - Exact-agreement and adjacent (+/-1) agreement rates
  - Mean signed error and MAE
  - Verbosity-bias diagnostics: corr(word_count, human_score), corr(word_count, system_score),
    corr(word_count, residual) where residual = system_score - human_score
  - A random-shuffle baseline (is the QWK distinguishable from chance pairing?)

Writes results_<version>.json (machine-readable) and prints a human-readable summary.
Run: python3 compute_qwk.py --version v1   (or v2, etc.)
"""

import argparse
import csv
import json
import os
import random
import statistics

from sklearn.metrics import cohen_kappa_score, confusion_matrix

HERE = os.path.dirname(os.path.abspath(__file__))


def pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def random_shuffle_baseline(human, system, labels, n_shuffles=2000, seed=42):
    rng = random.Random(seed)
    shuffled = system[:]
    kappas = []
    for _ in range(n_shuffles):
        rng.shuffle(shuffled)
        kappas.append(cohen_kappa_score(human, shuffled, weights="quadratic", labels=labels))
    return {
        "method": f"system_holistic_score randomly re-paired with human_score, "
                  f"{n_shuffles} shuffles, seed={seed}",
        "mean_qwk": statistics.mean(kappas),
        "sd_qwk": statistics.pstdev(kappas),
        "min_qwk": min(kappas),
        "max_qwk": max(kappas),
    }


def main(version, predictions_file, results_json):
    rows = []
    with open(predictions_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "essay_id": row["essay_id"],
                "human": int(row["human_score"]),
                "system": int(row["system_holistic_score"]),
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

    baseline = random_shuffle_baseline(human, system, all_labels)
    mode_qwk = cohen_kappa_score(human, [statistics.mode(human)] * n, weights="quadratic", labels=all_labels)
    stds_above_random = (qwk - baseline["mean_qwk"]) / baseline["sd_qwk"] if baseline["sd_qwk"] else float("nan")

    results = {
        "version": version,
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
                                    "during data recon before any grading",
        },
        "randomness_baseline": {
            **baseline,
            "always_predict_mode_qwk": mode_qwk,
            "actual_qwk_stds_above_random_mean": stds_above_random,
        },
    }

    with open(results_json, "w") as f:
        json.dump(results, f, indent=2)

    print(f"version: {version}")
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
    print(f"random-shuffle QWK baseline: mean={baseline['mean_qwk']:.4f} sd={baseline['sd_qwk']:.4f}")
    print(f"actual QWK is {stds_above_random:.2f} SDs above the random-pairing mean")
    print()
    print("Confusion matrix (rows=human, cols=system), labels=", all_labels)
    for label, row in zip(all_labels, cm):
        print(f"  human={label}: {row}")
    print()
    print(f"Wrote {results_json}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Rubric/prediction version, e.g. v1, v2")
    args = parser.parse_args()

    predictions_file = os.path.join(HERE, "..", "grading", f"predictions_{args.version}.csv")
    results_json = os.path.join(HERE, f"results_{args.version}.json")
    main(args.version, predictions_file, results_json)
