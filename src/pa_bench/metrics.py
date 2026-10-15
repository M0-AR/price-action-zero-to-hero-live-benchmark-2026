"""Trade-set metrics with uncertainty (no magic thresholds)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def summarize(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"n": 0, "win_rate": float("nan"), "avg_R": float("nan"), "expectancy": float("nan"),
                "profit_factor": float("nan"), "max_dd_R": float("nan"), "t_p": float("nan")}
    r = trades["R"].astype(float)
    wins = r[r > 0]
    loss = -r[r <= 0]
    pf = float(wins.sum() / loss.sum()) if loss.sum() > 0 else float("inf")
    eq = r.cumsum()
    dd = float((eq - eq.cummax()).min())
    try:
        t_p = float(stats.ttest_1samp(r, 0.0).pvalue) if len(r) >= 3 else float("nan")
    except Exception:
        t_p = float("nan")
    return {
        "n": int(len(r)),
        "win_rate": float((r > 0).mean()),
        "avg_R": float(r.mean()),
        "expectancy": float(r.mean()),
        "profit_factor": pf,
        "max_dd_R": dd,
        "t_p": t_p,
    }
