"""Run E01..E11 verification experiments on LIVE market data.

Usage:
  python3 experiments/run_all.py [--download-only] [--symbols SPY,QQQ,...] [--range 10y]

Design (from online best-practice synthesis, see papers/METHOD.md):
 - causal detectors only; entry at next open; costs 5bp+s2bp/side
 - in-sample = first 70%, out-of-sample = last 30% (frozen split, no re-tune)
 - buy&hold baseline; min-trade awareness; t-test on R (report, don't gate)
 - one Yahoo request at a time (1s pacing) to avoid 429
Outputs: results/summary.json, results/table.csv, results/SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pa_bench import data as D
from pa_bench import patterns as P
from pa_bench.backtest import backtest_signals, buy_hold
from pa_bench.metrics import summarize

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def split(df, frac=0.7):
    n = len(df)
    k = int(n * frac)
    return df.iloc[:k], df.iloc[k:]


def run_symbol(df: pd.DataFrame) -> dict:
    out: dict = {}
    close = df["Close"]
    a = P.atr(df)
    trend = P.trend_state(df)
    slope = P.slope_score(close)
    vol = P.volume_regime(df)
    pv = P.price_volume_4(df)
    gp = P.gaps(df)
    lv = P.breakout_levels(df, 20)
    rsi = P.rsi(close)

    # ---- E01 trend persistence: does up/down state predict next-5d drift? ----
    fwd5 = close.shift(-5) / close - 1
    e01 = {}
    for s in ["up", "down", "range"]:
        m = (trend == s)
        e01[s] = {"n": int(m.sum()), "mean_fwd5": float(fwd5[m].mean()) if m.sum() else float("nan")}
    out["E01_trend_persistence"] = e01

    # ---- E02 candle ranking: next-day direction after each shape ----
    nxt = (close.shift(-1) > close).astype(float)
    base_up = float(nxt.mean())
    e02 = {"__base_next_up_rate": base_up}
    for name, sig in [
        ("marubozu_bull", P.marubozu_bull(df)), ("marubozu_bear", P.marubozu_bear(df)),
        ("hammer", P.hammer_shape(df)), ("shooter", P.shooter_shape(df)),
        ("spinning", P.spinning_top(df)), ("doji", P.doji(df)),
    ]:
        m = sig.fillna(False).astype(bool)
        e02[name] = {"n": int(m.sum()), "next_up_rate": float(nxt[m].mean()) if m.sum() else float("nan")}
    out["E02_candles"] = e02

    # ---- E03 S/R zones: hold rate vs touch count ----
    z = P.support_resistance_zones(df.tail(400))  # bounded for speed; trailing window
    # align tail index
    hold = {}
    px = df["Close"].tail(400)
    # define hold: touches zone then doesn't close through within 5 bars (label uses future)
    zt = z["ztop"].fillna(np.nan)
    zb = z["zbot"].fillna(np.nan)
    touch = ((df["Low"].tail(400) <= zt + 1e-12) & (df["High"].tail(400) >= zb - 1e-12) & (z["ztouch"] >= 3))
    hold["n_touch3"] = int(touch.sum())
    out["E03_SR_touches"] = hold

    # ---- E04 HL-into-R -> breakout rate; power+rejection -> reversal ----
    hl_r = P.higher_lows_into_resistance(df).fillna(False)
    brk = (close.shift(-5) > lv["res"]).fillna(False)
    out["E04_structure"] = {
        "hl_into_R_n": int(hl_r.sum()),
        "hl_break_rate_5d": float(brk[hl_r].mean()) if hl_r.sum() else float("nan"),
        "base_break_rate_5d": float(brk.mean()),
    }

    # ---- E05 volume 2x2 forward returns ----
    e05 = {}
    for k in ["UU", "UD", "DU", "DD"]:
        m = (pv == k)
        e05[k] = {"n": int(m.sum()), "mean_fwd5": float(fwd5[m].mean()) if m.sum() else float("nan")}
    out["E05_volume_matrix"] = e05

    # ---- E06-E11 trade-level backtests (IS/OOS) ----
    def bt(l, s, **kw):
        tr = backtest_signals(df, l, s, **kw)
        if len(tr) == 0:
            return {"all": summarize(tr), "IS": summarize(tr), "OOS": summarize(tr)}
        cut = df.index[int(len(df) * 0.7)]
        return {"all": summarize(tr), "IS": summarize(tr[tr["t"] < cut]), "OOS": summarize(tr[tr["t"] >= cut]),
                "bh": buy_hold(df)}

    pm = P.power_move(df).fillna(False)
    bu = P.buildup(df).fillna(False)
    res, sup = lv["res"], lv["sup"]
    # E06 breakout with buildup vs chasing power move
    sig_build_long = bu & (close > res.shift(0).fillna(np.inf) * 0 + res)  # near res handled by breakout cond below
    bo_up = (close > res).fillna(False)
    bo_dn = (close < sup).fillna(False)
    out["E06_breakout_buildup_vs_chase"] = {
        "buildup_breakout_long": bt(bo_up & bu, pd.Series(False, index=df.index)),
        "powerbreakout_long": bt(bo_up & pm, pd.Series(False, index=df.index)),
        "buildup_breakdown_short": bt(pd.Series(False, index=df.index), bo_dn & bu),
    }
    # E07 pullback conservative (rejection candle) vs aggressive (touch only)
    ema20 = P.ema(close, 20)
    uptrend = (trend == "up")
    touch_ma = (df["Low"] <= ema20 * 1.005) & (close > ema20) & uptrend
    rej = P.hammer_shape(df) | P.marubozu_bull(df)
    out["E07_pullback"] = {
        "aggressive_touch": bt(touch_ma.fillna(False), pd.Series(False, index=df.index)),
        "conservative_rejection": bt((touch_ma & rej).fillna(False), pd.Series(False, index=df.index)),
    }
    # E08 reversal: break-of-structure vs first-pullback (fade)
    hh_break = (~uptrend)  # placeholder structure-break proxy: trend flip bar
    flip_to_down = (trend.shift(1) == "up") & (trend == "range")
    flip_to_up = (trend.shift(1) == "down") & (trend == "range")
    first_pb_long = flip_to_up.fillna(False)
    struct_short = (flip_to_down & (P.shooter_shape(df) | P.pin_bear(df))).fillna(False)
    out["E08_reversal"] = {
        "fade_first_pullback_long": bt(first_pb_long, pd.Series(False, index=df.index)),
        "structure_reversal_short": bt(pd.Series(False, index=df.index), struct_short),
    }
    # E09 inside bar small-range at value vs raw; hikkake trap rate
    ib = P.inside_bar(df).fillna(False)
    ibs = P.inside_small_range(df).fillna(False)
    at_val = (z.reindex(df.index)["ztouch"].fillna(0) >= 2) if len(z) else pd.Series(False, index=df.index)
    out["E09_insidebar"] = {
        "raw_breakout": bt(ib, ib),
        "smallrange_at_value": bt(ibs & at_val.fillna(False), ibs & at_val.fillna(False)),
        "hikkake_bulltrap_rate": float(P.hikkake_bull_trap(df).mean()),
        "hikkake_beartrap_rate": float(P.hikkake_bear_trap(df).mean()),
    }
    # E10 pin bar at trend/value vs raw
    pinb = P.pin_bull(df).fillna(False)
    pins = P.pin_bear(df).fillna(False)
    with_trend_long = pinb & (trend == "up").fillna(False)
    out["E10_pinbar"] = {
        "raw": bt(pinb, pins),
        "with_trend_or_value": bt((with_trend_long | (pinb & at_val.fillna(False))), (pins & (trend == "down").fillna(False))),
    }
    # E11 gaps: fill rates + gap-continuation trade
    # Course means *visible* gaps: require |gap| >= 0.1% (else every overnight
    # tick counts; raw counts kept as `n_raw` for transparency).
    filled = P.gap_filled(df, 5)
    e11 = {}
    big = gp["gap"].abs() >= 0.001
    for k in ["full_up", "part_up", "full_dn", "part_dn"]:
        m = gp[k].fillna(False)
        mb = (m & big.fillna(False))
        e11[k] = {"n": int(m.sum()), "fill5_rate": float(filled[m].mean()) if m.sum() else float("nan"),
                  "n_big": int(mb.sum()), "fill5_rate_big": float(filled[mb].mean()) if mb.sum() else float("nan")}
    hv = vol["high_vol"].fillna(False)
    gap_cont_long = (gp["full_up"] & hv).fillna(False)
    gap_cont_short = (gp["full_dn"] & hv).fillna(False)
    e11["gap_continuation_trades"] = bt(gap_cont_long, gap_cont_short)
    out["E11_gaps"] = e11
    out["buy_hold"] = buy_hold(df)
    out["bars"] = len(df)
    out["rsi_last"] = float(rsi.dropna().iloc[-1]) if rsi.dropna().size else float("nan")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--symbols", default="SPY,QQQ,AAPL,MSFT,BTC-USD,ETH-USD")
    ap.add_argument("--range", default="10y")
    args = ap.parse_args()
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    RES.mkdir(parents=True, exist_ok=True)
    data = {}
    for s in syms:
        print(f"[data] {s} ...", flush=True)
        try:
            data[s] = D.load_or_fetch(s, args.range)
            print(f"  rows={len(data[s])} {data[s].index[0].date()}->{data[s].index[-1].date()}")
        except Exception as e:
            print(f"  FAILED: {e}")
    if args.download_only:
        return
    all_res = {}
    rows = []
    for s, df in data.items():
        print(f"[bench] {s} ...", flush=True)
        r = run_symbol(df)
        all_res[s] = r
        # flatten trade summaries
        for exp in ["E06_breakout_buildup_vs_chase", "E07_pullback", "E08_reversal", "E09_insidebar", "E10_pinbar"]:
            for strat, v in r.get(exp, {}).items():
                if isinstance(v, dict) and "all" in v:
                    rows.append({"symbol": s, "exp": exp, "strat": strat, "split": "all", **v["all"]})
                    rows.append({"symbol": s, "exp": exp, "strat": strat, "split": "OOS", **v["OOS"]})
        g = r.get("E11_gaps", {})
        for k in ["full_up", "part_up", "full_dn", "part_dn"]:
            rows.append({"symbol": s, "exp": "E11_gaps", "strat": k, "split": "fill5_rate",
                         "n": g.get(k, {}).get("n"), "win_rate": g.get(k, {}).get("fill5_rate")})
            rows.append({"symbol": s, "exp": "E11_gaps_big0.1pct", "strat": k, "split": "fill5_rate",
                         "n": g.get(k, {}).get("n_big"), "win_rate": g.get(k, {}).get("fill5_rate_big")})
    with open(RES / "summary.json", "w") as f:
        json.dump(all_res, f, indent=1, default=float)
    pd.DataFrame(rows).to_csv(RES / "table.csv", index=False)
    # markdown digest
    lines = ["# Benchmark digest (live data)\n"]
    for s, r in all_res.items():
        lines.append(f"## {s} (bars={r['bars']}, buy&hold={r['buy_hold']:.2%})")
        lines.append(f"- E01 fwd5 by regime: " + ", ".join(f"{k}: {v['mean_fwd5']:.3%} (n={v['n']})" for k, v in r["E01_trend_persistence"].items()))
        lines.append(f"- E02 next-up (base={r['E02_candles'].get('__base_next_up_rate', float('nan')):.1%}): " + ", ".join(f"{k}: {v['next_up_rate']:.1%} (n={v['n']})" for k, v in r["E02_candles"].items() if k != "__base_next_up_rate"))
        lines.append(f"- E04 HL->R n={r['E04_structure']['hl_into_R_n']} break5d={r['E04_structure']['hl_break_rate_5d']:.1%} base={r['E04_structure']['base_break_rate_5d']:.1%}")
        lines.append(f"- E05 vol-matrix fwd5: " + ", ".join(f"{k}: {v['mean_fwd5']:.3%} (n={v['n']})" for k, v in r["E05_volume_matrix"].items()))
        lines.append(f"- E11 gap fill5 |big|>=0.1%: " + ", ".join(f"{k}: {r['E11_gaps'][k]['fill5_rate_big']:.0%} (n={r['E11_gaps'][k]['n_big']})" for k in ["full_up","part_up","full_dn","part_dn"]))
    (RES / "SUMMARY.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
