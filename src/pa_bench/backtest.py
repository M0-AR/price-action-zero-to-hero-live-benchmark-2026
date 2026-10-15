"""Event backtester: signal at close t -> enter at open t+1, no lookahead.

Long/short symmetric. Stop = k*ATR at signal bar; target = R*Risk;
time exit after `horizon` bars. Costs: commission + slippage per side,
charged on entry and exit. Returns per-trade R-net and bar-level equity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .patterns import atr


def backtest_signals(
    df: pd.DataFrame,
    signal_long: pd.Series,
    signal_short: pd.Series | None = None,
    k_atr: float = 1.5,
    R: float = 1.5,
    horizon: int = 10,
    commission: float = 0.0005,
    slippage: float = 0.0002,
) -> pd.DataFrame:
    a = atr(df, 14)
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    trades = []
    if signal_short is None:
        signal_short = pd.Series(False, index=df.index)
    signal_long = signal_long.reindex(df.index).fillna(False).astype(bool)
    signal_short = signal_short.reindex(df.index).fillna(False).astype(bool)
    for i in range(len(df) - 2):
        side = 0
        if signal_long.iloc[i]:
            side = 1
        elif signal_short.iloc[i]:
            side = -1
        else:
            continue
        if float(a.iloc[i]) != float(a.iloc[i]):  # NaN guard
            continue
        entry = float(o.iloc[i + 1])
        risk = k_atr * float(a.iloc[i])
        if risk <= 0 or entry <= 0:
            continue
        stop = entry - side * risk
        tgt = entry + side * R * risk
        cost_rate = commission + slippage
        exit_px, res = None, "time"
        for j in range(i + 1, min(len(df), i + 1 + horizon)):
            hb, lb = float(h.iloc[j]), float(l.iloc[j])
            if side == 1:
                hit_stop = lb <= stop
                hit_tgt = hb >= tgt
            else:
                hit_stop = hb >= stop
                hit_tgt = lb <= tgt
            # same-bar ambiguity: conservative -> stop first
            if hit_stop and hit_tgt:
                exit_px, res = stop, "stop"
                break
            if hit_stop:
                exit_px, res = stop, "stop"
                break
            if hit_tgt:
                exit_px, res = tgt, "target"
                break
        if exit_px is None:
            exit_px, res = float(c.iloc[min(len(df) - 1, i + horizon)]), "time"
        gross = side * (exit_px - entry) / entry
        # costs on notional both sides
        net = gross - 2 * cost_rate
        r_net = net * entry / risk
        trades.append({"t": df.index[i + 1], "side": side, "entry": entry, "exit": exit_px, "res": res, "ret_net": net, "R": r_net})
    return pd.DataFrame(trades)


def buy_hold(df: pd.DataFrame, commission: float = 0.0005, slippage: float = 0.0002) -> float:
    if len(df) < 2:
        return float("nan")
    return float(df["Close"].iloc[-1] / df["Open"].iloc[0] - 1 - 2 * (commission + slippage))
