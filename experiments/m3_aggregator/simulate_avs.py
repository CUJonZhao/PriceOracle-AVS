"""
PriceOracle-AVS Monte-Carlo simulator.

This script reproduces the *behavior* of our modified Aggregator
without depending on the actual Go binaries — handy while the team's
EigenLayer dev environment is still being set up. We use it to:

  (i)  validate that the median rule is robust to a small fraction
       of malicious / outlier operators;
  (ii) sweep the deviation-tolerance threshold to choose a defensible
       value for the slashing rule;
  (iii) generate publication-quality figures for §V of the paper.

The numbers used here (4-7 honest CEX prices, ~$3500 ETH/USD, 6 decimals)
match what the real Go aggregator will see in production.

Run:
    python3 simulate_avs.py --out figs/
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


# 6-decimal fixed-point convention: 3500_000000 == $3500.00
TRUE_PRICE = 3500_000000


# ----- algorithm: mirrors median.go semantics ---------------------------

def median_int(prices: List[int]) -> int:
    n = len(prices)
    if n == 0:
        return 0
    s = sorted(prices)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


def detect_outliers(prices: List[int], median_val: int, tol_pct: float) -> List[int]:
    if median_val == 0:
        return []
    threshold = median_val * tol_pct / 100.0
    return [i for i, p in enumerate(prices) if abs(p - median_val) > threshold]


# ----- scenario generators -----------------------------------------------

def honest_quote(rng: random.Random, true_price: int = TRUE_PRICE,
                 sigma_bps: float = 5.0) -> int:
    """Honest quote: small Gaussian noise (5 bp = 0.05% std)."""
    sigma = true_price * sigma_bps / 10_000.0
    return int(rng.gauss(true_price, sigma))


def malicious_quote(rng: random.Random, true_price: int = TRUE_PRICE,
                    bias_pct: float = None) -> int:
    """Malicious quote.

    A clever attacker varies their bias to dodge a fixed deviation
    threshold. We model this by drawing the bias uniformly from
    [2%, 12%] each round.
    """
    if bias_pct is None:
        bias_pct = rng.uniform(2.0, 12.0)
    sign = rng.choice([-1, 1])
    return int(true_price * (1 + sign * bias_pct / 100.0))


def simulate_round(n_total: int, n_malicious: int,
                   rng: random.Random) -> Tuple[List[int], int, int, List[int]]:
    quotes: List[int] = []
    indices = list(range(n_total))
    rng.shuffle(indices)
    bad = set(indices[:n_malicious])
    mal_idxs: List[int] = []
    for i in range(n_total):
        if i in bad:
            quotes.append(malicious_quote(rng))
            mal_idxs.append(i)
        else:
            quotes.append(honest_quote(rng))
    mean_v = int(round(statistics.fmean(quotes)))
    return quotes, mean_v, median_int(quotes), mal_idxs


# ----- experiments -------------------------------------------------------

def exp_robustness(n_total: int = 7, trials: int = 5000, seed: int = 0xBEEF) -> dict:
    """Median vs Mean error as the fraction of malicious operators grows."""
    rng = random.Random(seed)
    rows = []
    for n_mal in range(0, n_total + 1):
        med_errs, mean_errs = [], []
        for _ in range(trials):
            _, mean_v, med_v, _ = simulate_round(n_total, n_mal, rng)
            med_errs.append(abs(med_v - TRUE_PRICE) / TRUE_PRICE * 100)
            mean_errs.append(abs(mean_v - TRUE_PRICE) / TRUE_PRICE * 100)
        rows.append({
            "n_total": n_total,
            "n_malicious": n_mal,
            "frac_malicious": n_mal / n_total,
            "median_p50_err_pct": float(np.percentile(med_errs, 50)),
            "median_p95_err_pct": float(np.percentile(med_errs, 95)),
            "mean_p50_err_pct": float(np.percentile(mean_errs, 50)),
            "mean_p95_err_pct": float(np.percentile(mean_errs, 95)),
        })
    return {"rows": rows, "n_total": n_total, "trials": trials}


def exp_tolerance(n_total: int = 7, n_malicious: int = 2,
                  trials: int = 4000, seed: int = 0xCAFE) -> dict:
    """Sweep slashing tolerance threshold; emit ROC-style table."""
    rng = random.Random(seed)
    tols = [0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15]
    rows = []
    for tol in tols:
        fp = fn = tp = tn = 0
        for _ in range(trials):
            quotes, _, med, mal_idxs = simulate_round(n_total, n_malicious, rng)
            flagged = set(detect_outliers(quotes, med, tol))
            mal_set = set(mal_idxs)
            for i in range(n_total):
                if i in mal_set and i in flagged: tp += 1
                elif i in mal_set and i not in flagged: fn += 1
                elif i not in mal_set and i in flagged: fp += 1
                else: tn += 1
        total_mal = tp + fn
        total_hon = fp + tn
        rows.append({
            "tolerance_pct": tol,
            "true_positive_rate": tp / max(total_mal, 1),
            "false_positive_rate": fp / max(total_hon, 1),
            "true_negative_rate": tn / max(total_hon, 1),
            "false_negative_rate": fn / max(total_mal, 1),
        })
    return {"rows": rows, "n_total": n_total, "n_malicious": n_malicious}


def exp_latency(seed: int = 0xDEAD) -> dict:
    """Synthetic latency model: per-op quote + sign + 67% quorum + on-chain tx."""
    rng = np.random.default_rng(seed)
    sizes = [3, 5, 7, 10, 15, 20, 30]
    rows = []
    for n in sizes:
        latencies = []
        for _ in range(2000):
            quote_t = rng.gamma(2, 80, size=n)
            sign_t = rng.gamma(2, 15, size=n)
            arrival = quote_t + sign_t
            quorum_idx = int(np.ceil(n * 0.67)) - 1
            t_quorum = float(np.partition(arrival, quorum_idx)[quorum_idx])
            t_agg = rng.gamma(2, 8)
            t_chain = float(rng.normal(2000, 200))
            latencies.append(t_quorum + t_agg + t_chain)
        rows.append({
            "n_operators": n,
            "p50_ms": float(np.percentile(latencies, 50)),
            "p95_ms": float(np.percentile(latencies, 95)),
        })
    return {"rows": rows}


# ----- plotting ----------------------------------------------------------

def style_ieee():
    if not HAVE_MPL:
        return
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.grid": True,
        "grid.linewidth": 0.4,
        "grid.alpha": 0.4,
        "lines.linewidth": 1.6,
        "axes.linewidth": 0.6,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


def plot_robustness(data, path):
    rows = data["rows"]
    fracs = [r["frac_malicious"] for r in rows]
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    ax.plot(fracs, [r["median_p50_err_pct"] for r in rows], "o-", label="Median (P50)")
    ax.plot(fracs, [r["median_p95_err_pct"] for r in rows], "o--", label="Median (P95)", alpha=0.7)
    ax.plot(fracs, [r["mean_p50_err_pct"] for r in rows], "s-", label="Mean (P50)")
    ax.plot(fracs, [r["mean_p95_err_pct"] for r in rows], "s--", label="Mean (P95)", alpha=0.7)
    ax.set_xlabel("Fraction of malicious operators")
    ax.set_ylabel("Consensus error vs truth (%)")
    ax.set_title("Robustness ({} ops, {} trials)".format(data["n_total"], data["trials"]))
    ax.legend(loc="best")
    fig.savefig(path)
    fig.savefig(str(path).replace(".pdf", ".png"))
    plt.close(fig)


def plot_tolerance(data, path):
    rows = data["rows"]
    tols = [r["tolerance_pct"] for r in rows]
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    ax.plot(tols, [r["true_positive_rate"] for r in rows], "o-", label="TPR (slash bad ops)")
    ax.plot(tols, [r["false_positive_rate"] for r in rows], "s-", label="FPR (slash honest ops)")
    ax.set_xlabel("Tolerance threshold (%)")
    ax.set_ylabel("Rate")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Slashing-rule sensitivity ({}/{} malicious)".format(
        data["n_malicious"], data["n_total"]))
    ax.legend(loc="best")
    fig.savefig(path)
    fig.savefig(str(path).replace(".pdf", ".png"))
    plt.close(fig)


def plot_latency(data, path):
    rows = data["rows"]
    sizes = [r["n_operators"] for r in rows]
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    ax.plot(sizes, [r["p50_ms"] for r in rows], "o-", label="P50")
    ax.plot(sizes, [r["p95_ms"] for r in rows], "o--", label="P95", alpha=0.7)
    ax.set_xlabel("# operators")
    ax.set_ylabel("End-to-end latency (ms)")
    ax.set_title("Task latency vs operator count")
    ax.legend(loc="best")
    fig.savefig(path)
    fig.savefig(str(path).replace(".pdf", ".png"))
    plt.close(fig)


# ----- entry-point -------------------------------------------------------

def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="figs", help="Output directory")
    ap.add_argument("--no-plot", action="store_true", help="Skip plots, just emit CSV")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Running experiment 1: median robustness...")
    rob = exp_robustness()
    write_csv(out / "results_robustness.csv", rob["rows"], list(rob["rows"][0].keys()))

    print("Running experiment 2: tolerance sensitivity...")
    tol = exp_tolerance()
    write_csv(out / "results_tolerance.csv", tol["rows"], list(tol["rows"][0].keys()))

    print("Running experiment 3: aggregation latency...")
    lat = exp_latency()
    write_csv(out / "results_latency.csv", lat["rows"], list(lat["rows"][0].keys()))

    if HAVE_MPL and not args.no_plot:
        style_ieee()
        plot_robustness(rob, out / "fig_v1_median_robustness.pdf")
        plot_tolerance(tol, out / "fig_v2_tolerance_sensitivity.pdf")
        plot_latency(lat, out / "fig_v3_aggregation_latency.pdf")
        print("Wrote 3 PDFs (and PNG copies) to {}/".format(out))
    else:
        print("matplotlib unavailable or --no-plot set; only CSV emitted.")


if __name__ == "__main__":
    main()
