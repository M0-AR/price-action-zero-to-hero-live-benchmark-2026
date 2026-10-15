"""Generate README/preview visual assets from verified results (offline).

Outputs (assets/ + results/figures/):
  gap_gradient.png, regime_drift.png, volume_matrix.png, candles_vs_base.png,
  demo.gif (animated SPY regime sweep), preview_thumb.png (first GIF frame)
Style: dark, GitHub-friendly. No network.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parents[1]
RES = json.load(open(ROOT / "results" / "summary.json"))
SYMS = [s for s in ["SPY", "QQQ", "AAPL", "MSFT"] if s in RES]
A = ROOT / "assets"
F = ROOT / "results" / "figures"
A.mkdir(exist_ok=True); F.mkdir(exist_ok=True)

plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                     "text.color": "white", "axes.labelcolor": "white",
                     "xtick.color": "white", "ytick.color": "white",
                     "axes.edgecolor": "#30363d", "grid.color": "#21262d"})
GREEN, RED, BLUE, GOLD = "#2ea043", "#f85149", "#58a6ff", "#d29922"


def save_both(fig, name):
    fig.tight_layout()
    fig.savefig(A / name, dpi=110, bbox_inches="tight")
    fig.savefig(F / name, dpi=110, bbox_inches="tight")
    plt.close(fig)


# 1. Gap-fill gradient -------------------------------------------------------
cats = ["full_up", "part_up", "full_dn", "part_dn"]
labels = ["Full gap\nup", "Partial gap\nup", "Full gap\ndown", "Partial gap\ndown"]
x = np.arange(len(cats)); w = 0.18
fig, ax = plt.subplots(figsize=(9, 4.5))
for i, s in enumerate(SYMS):
    v = [RES[s]["E11_gaps"][c]["fill5_rate_big"] * 100 for c in cats]
    ax.bar(x + (i - 1.5) * w, v, w, label=s)
ax.axhline(90, color=RED, ls="--", lw=1, label='Course claim "90%"')
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("Filled within 5 days (%)"); ax.set_title("Gap-fill gradient: partial downs fill most, full ups least")
ax.legend(ncols=5, fontsize=8); ax.set_ylim(0, 100); ax.grid(axis="y", alpha=0.4)
save_both(fig, "gap_gradient.png")

# 2. Regime drift ------------------------------------------------------------
regs = ["up", "down", "range"]
x = np.arange(len(regs)); w = 0.18
fig, ax = plt.subplots(figsize=(8, 4.2))
for i, s in enumerate(SYMS):
    v = [RES[s]["E01_trend_persistence"][r]["mean_fwd5"] * 100 for r in regs]
    ax.bar(x + (i - 1.5) * w, v, w, label=s)
ax.set_xticks(x); ax.set_xticklabels(["Uptrend", "Downtrend", "Range"])
ax.set_ylabel("Avg next-5-day drift (%)"); ax.set_title("Downtrends snap back hardest (mean-reversion)")
ax.legend(ncols=4, fontsize=8); ax.grid(axis="y", alpha=0.4)
save_both(fig, "regime_drift.png")

# 3. Volume matrix (pooled mean fwd5) -----------------------------------------
cells = ["UU", "UD", "DU", "DD"]
names = ["Up +\nhigh vol", "Up +\nlow vol", "Down +\nhigh vol", "Down +\nlow vol"]
vals = [np.mean([RES[s]["E05_volume_matrix"][c]["mean_fwd5"] * 100 for s in SYMS]) for c in cells]
fig, ax = plt.subplots(figsize=(8, 4.2))
cols = [BLUE, BLUE, GREEN, GOLD]
ax.bar(names, vals, color=cols)
ax.set_ylabel("Avg next-5-day drift, pooled (%)")
ax.set_title("Volume inversion: high-volume down days bounce most")
ax.grid(axis="y", alpha=0.4)
save_both(fig, "volume_matrix.png")

# 4. Candles vs base ---------------------------------------------------------
shapes = [("marubozu_bull", "Marubozu\nbull"), ("marubozu_bear", "Marubozu\nbear"),
          ("hammer", "Hammer"), ("shooter", "Shooting\nstar"),
          ("spinning", "Spinning\ntop"), ("doji", "Doji")]
base = np.mean([RES[s]["E02_candles"]["__base_next_up_rate"] * 100 for s in SYMS])
vals = [np.mean([RES[s]["E02_candles"][k]["next_up_rate"] * 100 for s in SYMS]) for k, _ in shapes]
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar([l for _, l in shapes], vals, color=[RED if v < base else GREEN for v in vals])
ax.axhline(base, color=GOLD, ls="--", label=f"Base rate {base:.1f}%")
ax.set_ylabel("Next-day up probability, pooled (%)")
ax.set_title("Candlesticks vs base rate: only the shooting star stands out")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.4)
save_both(fig, "candles_vs_base.png")

# 5. Animated demo GIF: SPY regime sweep --------------------------------------
df = pd.read_csv(ROOT / "data" / "SPY_10y.csv", parse_dates=["Date"], index_col="Date")
px = df["Close"]
norm = px / px.iloc[0]
N = 60
idx = np.linspace(0, len(px) - 1, N).astype(int)
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.set_xlim(px.index[0], px.index[-1]); ax.set_ylim(norm.min() * 0.95, norm.max() * 1.05)
ax.set_title("SPY 2016-2026: +260% buy-and-hold — the benchmark every strategy must beat")
ax.set_ylabel("Growth of $1"); ax.grid(alpha=0.3)
(line,) = ax.plot([], [], color=GREEN, lw=1.6)
txt = ax.text(0.02, 0.94, "", transform=ax.transAxes, fontsize=10, color=GOLD)


def upd(f):
    j = idx[f]
    line.set_data(px.index[: j + 1], norm.iloc[: j + 1])
    txt.set_text(f"{px.index[j].date()}  ${px.iloc[j]:.0f}")
    return line, txt


ani = FuncAnimation(fig, upd, frames=N, interval=90, blit=False)
ani.save(A / "demo.gif", writer=PillowWriter(fps=12))
ani.save(F / "demo.gif", writer=PillowWriter(fps=12))
plt.close(fig)
print("assets written:", sorted(p.name for p in A.iterdir()))
