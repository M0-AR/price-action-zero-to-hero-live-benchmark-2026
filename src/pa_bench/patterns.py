"""Deterministic price-action pattern detectors (daily bars).

Every function uses only data at or before bar t (no lookahead).
Conventions: df columns Open/High/Low/Close/Volume. All detectors return
boolean Series aligned with df (signal known at bar close t, executed at
open t+1 by the backtester).

Implements the course transcript claims:
 swing/trend (HH/HL/LH/LL, slope, duration), marubozu, hammer/hanging-man,
 shooting-star/inverted-hammer, spinning-top, doji, inside-bar (+small-range,
 multiple, hikkake), pin-bar (wick>=2*body), S/R zones (>=3 touches spaced in
 time), volume 2x2 matrix, gaps (full/partial up/down), breakout/pullback/
 reversal structures, RSI(14) convergence filter.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean().replace(0, np.nan)
    rs = up / dn
    return 100 - 100 / (1 + rs)


def swings(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """Fractal swings with k bars each side."""
    h, l = df["High"], df["Low"]
    sh = h[(h == h.rolling(2 * k + 1, center=True).max())]
    sl = l[(l == l.rolling(2 * k + 1, center=True).min())]
    out = pd.DataFrame({"swing_high": h.index.isin(sh.dropna().index), "swing_low": l.index.isin(sl.dropna().index)}, index=df.index)
    return out


def trend_state(df: pd.DataFrame, lookback: int = 60, k: int = 2) -> pd.Series:
    """Uptrend if last two swing highs AND last two swing lows both rise;
    downtrend if both fall; else 'range'. Computed causally via expanding scan."""
    sw = swings(df, k)
    states = []
    for i in range(len(df)):
        highs = df.index[: i + 1][sw["swing_high"].iloc[: i + 1]]
        lows = df.index[: i + 1][sw["swing_low"].iloc[: i + 1]]
        if len(highs) < 2 or len(lows) < 2:
            states.append("range")
            continue
        h1, h2 = df.loc[highs[-2], "High"], df.loc[highs[-1], "High"]
        l1, l2 = df.loc[lows[-2], "Low"], df.loc[lows[-1], "Low"]
        # restrict to recent lookback window
        if (df.index[i] - highs[-2]).days > lookback * 1.5:
            states.append("range")
            continue
        if h2 > h1 and l2 > l1:
            states.append("up")
        elif h2 < h1 and l2 < l1:
            states.append("down")
        else:
            states.append("range")
    return pd.Series(states, index=df.index)


def slope_score(close: pd.Series, n: int = 20) -> pd.Series:
    """Rolling linear-regression slope of close, z-scored (trend strength proxy)."""
    def _s(y):
        if len(y) < n or y.isna().any():
            return np.nan
        x = np.arange(n)
        return np.polyfit(x, y.values, 1)[0] / (y.mean() or np.nan)

    return close.rolling(n).apply(_s, raw=False)


def _body(df):
    return (df["Close"] - df["Open"]).abs()


def _rng(df):
    return (df["High"] - df["Low"]).replace(0, np.nan)


def marubozu_bull(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    return (df["Close"] > df["Open"]) & (b / r > 0.85) & (uw / r < 0.08) & (lw / r < 0.08)


def marubozu_bear(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    return (df["Close"] < df["Open"]) & (b / r > 0.85) & (uw / r < 0.08) & (lw / r < 0.08)


def hammer_shape(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    return (lw >= 2 * b) & (uw <= b * 1.0) & (b / r < 0.35) & (r > 0)


def shooter_shape(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    return (uw >= 2 * b) & (lw <= b * 1.0) & (b / r < 0.35) & (r > 0)


def spinning_top(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    return (b / r <= 0.3) & (uw >= b) & (lw >= b) & (r > 0)


def doji(df: pd.DataFrame) -> pd.Series:
    b, r = _body(df), _rng(df)
    return (b / r <= 0.08) & (r > 0)


def inside_bar(df: pd.DataFrame) -> pd.Series:
    return (df["High"] < df["High"].shift(1)) & (df["Low"] > df["Low"].shift(1))


def inside_small_range(df: pd.DataFrame, n: int = 14, frac: float = 0.6) -> pd.Series:
    ib = inside_bar(df)
    return ib & ((_rng(df)) < frac * atr(df, n))


def inside_multiple(df: pd.DataFrame, m: int = 2) -> pd.Series:
    ib = inside_bar(df).astype(int)
    # simpler: rolling sum >= m
    return ib.rolling(m).sum() >= m


def hikkake_bull_trap(df: pd.DataFrame) -> pd.Series:
    """Bearish hikkake: inside bar then break above mother high then close back inside (trap longs)."""
    ib = inside_bar(df)
    mh = df["High"].shift(1)
    broke_up = (df["High"] > mh) & (df["Close"] < mh)
    return ib.shift(1) & broke_up


def hikkake_bear_trap(df: pd.DataFrame) -> pd.Series:
    ib = inside_bar(df)
    ml = df["Low"].shift(1)
    broke_dn = (df["Low"] < ml) & (df["Close"] > ml)
    return ib.shift(1) & broke_dn


def pin_bar(df: pd.DataFrame, mult: float = 2.0) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    longwick = pd.concat([uw, lw], axis=1).max(axis=1)
    return (longwick >= mult * b) & (b / r <= 0.4) & (r > 0)


def pin_bull(df: pd.DataFrame, mult: float = 2.0) -> pd.Series:
    b, r = _body(df), _rng(df)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    return (lw >= mult * b) & (uw <= b) & (b / r <= 0.4)


def pin_bear(df: pd.DataFrame, mult: float = 2.0) -> pd.Series:
    b, r = _body(df), _rng(df)
    uw = df["High"] - df[["Close", "Open"]].max(axis=1)
    lw = df[["Close", "Open"]].min(axis=1) - df["Low"]
    return (uw >= mult * b) & (lw <= b) & (b / r <= 0.4)


def support_resistance_zones(df: pd.DataFrame, lookback: int = 252, min_touches: int = 3, min_gap: int = 10):
    """Cluster swing highs/lows of last `lookback` bars within 0.5*ATR.
    Returns DataFrame with zone_mid, zone_top, zone_bot, touches, kind, updated causally-ish
    (recomputed per bar on trailing window -> no lookahead). Heavy; computed sparsely in backtest."""
    a = atr(df, 14)
    sw = swings(df, 2)
    mids, tops, bots, kinds, touches = [], [], [], [], []
    idx = df.index
    for i in range(len(df)):
        lo = max(0, i - lookback + 1)
        win = df.iloc[lo : i + 1]
        swh = win.index[sw["swing_high"].iloc[lo : i + 1].values]
        swl = win.index[sw["swing_low"].iloc[lo : i + 1].values]
        levels = [(float(df.loc[t, "High"]), "R", t) for t in swh] + [(float(df.loc[t, "Low"]), "S", t) for t in swl]
        ai = float(a.iloc[i]) if not np.isnan(a.iloc[i]) else float((df["High"] - df["Low"]).iloc[lo : i + 1].mean())
        tol = 0.5 * ai
        px = float(df["Close"].iloc[i])
        best = None
        # group levels near current price
        cands = [lv for lv in levels if abs(lv[0] - px) <= 2.5 * ai]
        # cluster cands
        clusters: list[list] = []
        for lv in sorted(cands):
            if clusters and abs(lv[0] - np.mean([c[0] for c in clusters[-1]])) <= tol:
                clusters[-1].append(lv)
            else:
                clusters.append([lv])
        scored = []
        for cl in clusters:
            times = sorted([c[2] for c in cl])
            # count touches spaced >= min_gap bars
            kept = []
            for t in times:
                if not kept or (t - kept[-1]).days >= min_gap or (df.index.get_loc(t) - df.index.get_loc(kept[-1]) >= min_gap):
                    kept.append(t)
            if len(kept) >= min_touches:
                mid = float(np.mean([c[0] for c in cl]))
                scored.append((abs(mid - px), mid, cl[0][1], len(kept)))
        if scored:
            scored.sort()
            _, mid, kind, n = scored[0]
            mids.append(mid)
            tops.append(mid + tol)
            bots.append(mid - tol)
            kinds.append(kind)
            touches.append(n)
        else:
            mids.append(np.nan)
            tops.append(np.nan)
            bots.append(np.nan)
            kinds.append("")
            touches.append(0)
    return pd.DataFrame({"zmid": mids, "ztop": tops, "zbot": bots, "zkind": kinds, "ztouch": touches}, index=idx)


def volume_regime(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    avg = df["Volume"].rolling(n).mean()
    ratio = df["Volume"] / avg
    return pd.DataFrame({"vol_avg": avg, "vol_ratio": ratio, "high_vol": ratio > 1.0, "strong_vol": ratio > 1.5}, index=df.index)


def price_volume_4(df: pd.DataFrame, n: int = 10) -> pd.Series:
    """Course's 2x2: UU=bullish, UD=bull-trap-caution, DU=bearish, DD=bear-trap-caution."""
    ret = df["Close"].pct_change()
    vr = volume_regime(df, n)["vol_ratio"]
    conds = [
        (ret > 0) & (vr > 1.0),
        (ret > 0) & (vr <= 1.0),
        (ret < 0) & (vr > 1.0),
        (ret <= 0) & (vr <= 1.0),
    ]
    return pd.Series(np.select(conds, ["UU", "UD", "DU", "DD"], default="flat"), index=df.index)


def gaps(df: pd.DataFrame) -> pd.DataFrame:
    prev_close = df["Close"].shift(1)
    prev_high = df["High"].shift(1)
    prev_low = df["Low"].shift(1)
    gap = (df["Open"] - prev_close) / prev_close
    full_up = df["Open"] > prev_high
    part_up = (df["Open"] > prev_close) & (df["Open"] <= prev_high)
    full_dn = df["Open"] < prev_low
    part_dn = (df["Open"] < prev_close) & (df["Open"] >= prev_low)
    return pd.DataFrame(
        {"gap": gap, "full_up": full_up.fillna(False), "part_up": part_up.fillna(False), "full_dn": full_dn.fillna(False), "part_dn": part_dn.fillna(False)},
        index=df.index,
    )


def gap_filled(df: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """90%-fill claim: does price retrace to prev close within `horizon` bars? (uses future -> label only)."""
    prev_close = df["Close"].shift(1)
    out = pd.Series(False, index=df.index)
    for i in range(len(df)):
        pc = prev_close.iloc[i]
        if np.isnan(pc):
            continue
        o = df["Open"].iloc[i]
        fwd = df.iloc[i + 1 : i + 1 + horizon]
        if len(fwd) == 0:
            continue
        if o > pc:
            out.iloc[i] = (fwd["Low"] <= pc).any()
        elif o < pc:
            out.iloc[i] = (fwd["High"] >= pc).any()
        else:
            out.iloc[i] = True
    return out


def breakout_levels(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Donchian-style reference levels (causal, shifted)."""
    return pd.DataFrame({"res": df["High"].rolling(n).max().shift(1), "sup": df["Low"].rolling(n).min().shift(1)}, index=df.index)


def higher_lows_into_resistance(df: pd.DataFrame, n: int = 20) -> pd.Series:
    lv = breakout_levels(df, n)
    sw = swings(df, 2)
    a = atr(df, 14)
    out = pd.Series(False, index=df.index)
    for i in range(5, len(df)):
        win = df.iloc[max(0, i - n) : i]
        lows = win.index[sw["swing_low"].iloc[max(0, i - n) : i].values]
        if len(lows) < 2:
            continue
        l1, l2 = float(df.loc[lows[-2], "Low"]), float(df.loc[lows[-1], "Low"])
        r = lv["res"].iloc[i]
        if np.isnan(r):
            continue
        ai = float(a.iloc[i]) if not np.isnan(float(a.iloc[i])) else 0.0
        near = (float(df["Close"].iloc[i]) >= r - 0.5 * ai) and (float(df["Close"].iloc[i]) <= r + 0.25 * ai)
        if l2 > l1 and near:
            out.iloc[i] = True
    return out


def power_move(df: pd.DataFrame, mult: float = 1.5, n: int = 14) -> pd.Series:
    return _rng(df) > mult * atr(df, n)


def buildup(df: pd.DataFrame, m: int = 5, frac: float = 0.7, n: int = 14) -> pd.Series:
    return (_rng(df).rolling(m).mean() < frac * atr(df, n))
