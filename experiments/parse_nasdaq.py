"""Parse a Nasdaq historical JSON dump to repo CSV cache (offline)."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/home/md/src/price-action-zero-to-hero-live-benchmark-2026")


def num(x):
    s = str(x).replace("$", "").replace(",", "").strip()
    return float(s) if s and s.lower() != "nan" else float("nan")


def main(path, symbol, out):
    j = json.load(open(path))
    rows = j["data"]["tradesTable"]["rows"]
    recs = []
    for r in rows:
        v = str(r["volume"]).replace(",", "").strip() or "0"
        recs.append(
            (
                pd.to_datetime(r["date"]),
                num(r["open"]),
                num(r["high"]),
                num(r["low"]),
                num(r["close"]),
                int(float(v)),
            )
        )
    df = (
        pd.DataFrame(recs, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        .set_index("Date")
        .sort_index()
    )
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Symbol"] = symbol
    df.index.name = "Date"
    df.to_csv(ROOT / "data" / out)
    print(f"saved {symbol}", len(df), df.index[0].date(), "->", df.index[-1].date())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
