"""Live market data loader.

Source: Yahoo Finance chart API v8 (query2 host + browser User-Agent).
Verified working 2026-10-15 from this host. Findings from verification:
 - query1 host returns "Edge: Too Many Requests" (use query2).
 - Python urllib gets HTTP 429 while curl with the same UA succeeds
   (TLS/edge fingerprinting), so fetching goes through curl subprocess.
 - Yahoo allows only a few requests/minute from this egress: 20-30 s
   pacing between symbols + 30/60/120 s backoff on 429.
No API key. Daily OHLCV (unadjusted -- splits/dividends cause level jumps;
disclosed as limitation L2 in papers/METHOD.md). CSV cache under data/.
Nasdaq api.nasdaq.com is the automatic fallback for US listings.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pandas as pd

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
# NOTE (verified 2026-10-15): the `events=div,split` query param triggers
# HTTP 429 from this egress while the same URL without it succeeds, so we
# fetch unadjusted OHLCV and disclose it (see papers/METHOD.md limitation L2).
BASE = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range={rng}"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _curl_json(url: str, timeout: int = 40, extra_headers: list | None = None) -> dict:
    cmd = ["curl", "-sL", "--max-time", str(timeout), "-A", UA]
    for h in extra_headers or []:
        cmd += ["-H", h]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True)
    body = (p.stdout or "").strip()
    if not body or body.startswith("Edge:") or body == "Too Many Requests":
        raise RuntimeError(f"rate-limited (body={body[:60]!r})")
    return json.loads(body)


def _fetch_nasdaq(symbol: str) -> pd.DataFrame:
    """Fallback for US listings: api.nasdaq.com historical tables (verified 2026-10-15).
    SPY/QQQ are assetclass=etf, AAPL/MSFT are stocks."""
    asset = "etf" if symbol in ("SPY", "QQQ") else "stocks"
    url = f"https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass={asset}&fromdate=2015-01-01&limit=9999"
    payload = _curl_json(url, extra_headers=["Accept: application/json"])
    rows = payload["data"]["tradesTable"]["rows"]
    recs = []
    for r in rows:
        def num(x):
            return float(str(x).replace("$", "").replace(",", "").strip() or "nan")
        recs.append((pd.to_datetime(r["date"]), num(r["open"]), num(r["high"]), num(r["low"]), num(r["close"]), int(str(r["volume"]).replace(",", "").strip() or 0)))
    df = pd.DataFrame(recs, columns=["Date", "Open", "High", "Low", "Close", "Volume"]).set_index("Date").sort_index()
    df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Symbol"] = symbol
    return df


def fetch_daily(symbol: str, rng: str = "10y") -> pd.DataFrame:
    """Download daily OHLCV for `symbol` via curl, with backoff (max 4 tries)."""
    url = BASE.format(sym=symbol, rng=rng)
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            payload = _curl_json(url)
            result = payload["chart"]["result"][0]
            ts = result["timestamp"]
            q = result["indicators"]["quote"][0]
            adj = None
            try:
                adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
            except Exception:
                adj = None
            df = pd.DataFrame(
                {
                    "Open": q.get("open"),
                    "High": q.get("high"),
                    "Low": q.get("low"),
                    "Close": q.get("close"),
                    "Volume": q.get("volume"),
                },
                index=pd.to_datetime(ts, unit="s", utc=True),
            )
            df.index = df.index.tz_convert("America/New_York").tz_localize(None)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            df["Volume"] = df["Volume"].fillna(0)
            if adj is not None:
                try:
                    adj_s = pd.Series(adj, index=df.index)
                    factor = (adj_s / df["Close"]).replace([float("inf")], float("nan")).ffill().bfill().fillna(1.0)
                    for c in ["Open", "High", "Low", "Close"]:
                        df[c] = df[c] * factor
                except Exception:
                    pass
            df.index.name = "Date"
            df["Symbol"] = symbol
            return df
        except Exception as e:  # noqa: BLE001 - backoff then raise
            last_err = e
            time.sleep(30 * (attempt + 1))
    # Yahoo persistently throttled -> Nasdaq fallback for US listings
    if "-" not in symbol and "=" not in symbol and symbol.isupper():
        try:
            return _fetch_nasdaq(symbol)
        except Exception as e2:  # noqa: BLE001
            raise RuntimeError(f"fetch_daily({symbol}) yahoo failed ({last_err}) + nasdaq failed ({e2})")
    raise RuntimeError(f"fetch_daily({symbol}) failed after 4 tries: {last_err}")


def load_or_fetch(symbol: str, rng: str = "10y", refresh: bool = False) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol.replace('=','').replace('-','_')}_{rng}.csv"
    if path.exists() and not refresh:
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        return df
    df = fetch_daily(symbol, rng)
    df.to_csv(path)
    time.sleep(25.0)  # one request at a time, paced; avoids 429
    return df


UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "BTC-USD", "ETH-USD", "EURUSD=X", "GC=F"]
