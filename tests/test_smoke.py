"""Smoke tests: deterministic, offline (banked SPY CSV only, no network)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pa_bench import patterns as P
from pa_bench.backtest import backtest_signals
from pa_bench.metrics import summarize

DATA = Path(__file__).resolve().parents[1] / "data" / "SPY_10y.csv"


def _spy():
    assert DATA.exists(), "banked SPY CSV missing -- run downloads first"
    return pd.read_csv(DATA, parse_dates=["Date"], index_col="Date")


def test_no_lookahead_execution():
    df = _spy()
    sig = P.marubozu_bull(df).fillna(False)
    tr = backtest_signals(df, sig, None)
    # entries must be next-open prices present in data
    assert set(tr["entry"].round(6)).issubset(set(df["Open"].round(6)))


def test_metrics_sane():
    df = _spy()
    tr = backtest_signals(df, P.inside_bar(df).fillna(False), P.inside_bar(df).fillna(False))
    s = summarize(tr)
    assert s["n"] > 50 and 0 <= s["win_rate"] <= 1


def test_gap_labels_bounded():
    df = _spy()
    f = P.gap_filled(df, 5)
    assert f.mean() > 0.3 and f.mean() < 1.0
