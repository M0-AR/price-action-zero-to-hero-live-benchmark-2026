"""Background bulk downloader: sequential, paced, resumable. Skips cached CSVs."""
import sys, time
sys.path.insert(0, "/home/md/src/price-action-zero-to-hero-live-benchmark-2026/src")
from pathlib import Path
from pa_bench.data import load_or_fetch

SYMS = ["QQQ", "AAPL", "MSFT", "BTC-USD", "ETH-USD", "EURUSD=X", "GC=F"]
LOG = Path("/home/md/src/price-action-zero-to-hero-live-benchmark-2026/data/dl.log")

def log(m):
    with open(LOG, "a") as f:
        f.write(m + "\n")
    print(m, flush=True)

for s in SYMS:
    out = Path(f"/home/md/src/price-action-zero-to-hero-live-benchmark-2026/data/{s.replace('=','').replace('-','_')}_10y.csv")
    if out.exists() and out.stat().st_size > 10000:
        log(f"SKIP {s} cached")
        continue
    try:
        df = load_or_fetch(s, "10y", refresh=True)
        log(f"OK {s} rows={len(df)} {df.index[0].date()}->{df.index[-1].date()}")
    except Exception as e:
        log(f"FAIL {s}: {e}")
    time.sleep(45)
log("DONE")
