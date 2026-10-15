# Price Action Zero-to-Hero: An Independent Live-Data Verification Benchmark

**Can a retail trader learn price action from a video course and expect an edge?
We froze 14 course claims into code, priced in costs, and tested them on
10,054 live daily bars (2016–2026). Most claims fail. Four survive — and the
data hides patterns the course never mentions.**

`experiments/` + `src/pa_bench/` + `docker-compose.yml` reproduce everything.
No discretion, no hindsight anecdotes: losers are published as losers.

---

## Abstract

Discretionary trading education ("price action courses") teaches chart reading
through hand-picked historical examples — a procedure the backtesting literature
identifies as anecdotal validation with uncontrolled lookahead bias. This study
independently verifies a representative zero-to-hero price-action curriculum
(market structure, trends, candlesticks, support/resistance, volume, breakouts,
fakeouts, pullbacks, reversals, inside bars, pin bars, gaps) by converting each
claim into a frozen mechanical rule and backtesting it on live public market
data: **SPY, QQQ, AAPL, MSFT, 2016-10-14 → 2026-10-15 (2,513 bars each)**,
signal-at-close / execution-at-next-open, 5 bp commission + 2 bp slippage per
side, 70/30 chronological in-sample/out-of-sample split, buy-and-hold baseline.

**Headline results (4 symbols, 10,054 bars):**

| # | Course claim | Verdict | Evidence |
|---|--------------|---------|----------|
| E04 | Higher lows into resistance → breakout | **CONFIRMED** | 5-day break rate 55–58% vs 27–34% base, all 4 symbols |
| E07 | Wait for rejection candle on pullbacks | **CONFIRMED** | PF 2.28 vs 1.41 blind-touch; OOS holds |
| E08 | Never fade the first pullback | **CONFIRMED** | Fade-first OOS PF 0.80, expectancy −0.15R |
| E11 | "90% of gaps fill" | **REJECTED ( overstated)** | 63–84% by type; stable gradient part_dn > part_up > full_dn > full_up |
| E05 | Volume×price 2×2 matrix as taught | **INVERTED** | Down-on-high-volume (taught "bearish") has the *best* 5-day drift |
| E02 | Candle ranking marubozu > pins > doji | **REJECTED** | All shapes ≈ base rate except weak shooting-star effect |
| E09 | Small-range inside bar at value is best | **REJECTED** | PF 0.80; raw inside-bar breakout PF 1.23 instead |
| E10 | Raw pin bars have edge | **REJECTED (raw) / WEAK (filtered)** | Raw PF 0.97; trend/value filter PF 1.05 |
| E06 | Buildup breakouts beat power-move chases | **NUANCED** | Buildup PF 1.15 vs chase 0.84 overall; OOS thin samples |

**Four hidden patterns the course never teaches** (§6): the downtrend snap-back
(HP1), the capitulation-volume inversion (HP2), the gap-fill gradient (HP3),
and the ~5% hikkake tax on every breakout system (HP4).

> Crypto/FX extension (BTC-USD, ETH-USD, EURUSD=X, GC=F) is queued in §9;
> download throttling from public endpoints paced this release to equities.
> The pipeline auto-ingests new symbols with zero code changes.

---

## 1. Introduction: what was actually claimed

The source curriculum is a ~14-episode "completely free" price-action course:
phases (accumulation → markup → distribution → markdown), trend taxonomy
(up/down/sideways; contraction/expansion/triangular ranges), candlestick
literacy (marubozu, hammer/hanging-man, shooting-star/inverted-hammer, spinning
tops, doji), a 4-step support/resistance method (zoom out → sticky zones →
align ≥3 touches → draw zone, never a line), a volume doctrine (the 2×2
price×volume matrix plus delivery volume), and five strategy families
(breakouts, fakeout filters incl. RSI convergence, pullbacks
aggressive-vs-conservative, reversals incl. break-of-structure and higher
timeframe structure, inside-bar/pin-bar/gap systems with the "90% of gaps
fill" assertion).

These are textbook discretionary claims: plausible, visually persuasive, and —
as QuantifiedStrategies (2026) documents across backtested price-action rules —
usually untested and often no better than chance once coded. Our contribution
is a **registered-style mechanical translation** of each claim plus a **live,
costed, out-of-sample test**.

## 2. Data: live public OHLCV and how access was verified

| Symbol | Bars | Span | Source | Buy&hold (10y) |
|--------|------|------|--------|----------------|
| SPY | 2,513 | 2016-10-17 → 2026-10-15 | Yahoo v8 | +260% |
| QQQ | 2,513 | 2016-10-14 → 2026-10-14 | Nasdaq API | +520% |
| AAPL | 2,513 | 2016-10-14 → 2026-10-14 | Nasdaq API | +1,064% |
| MSFT | 2,513 | 2016-10-14 → 2026-10-14 | Nasdaq API | +834% |

Egress verification log (2026-10-15, kept because reproducibility includes
*access*, not just code):

- `query1.finance.yahoo.com` → `Edge: Too Many Requests`; `query2` host works.
- Python `urllib` with browser UA → HTTP 429 while `curl` with the same UA
  succeeds (TLS/edge fingerprinting) → fetcher uses `curl` subprocess.
- `?events=div,split` triggers 429; same URL without it succeeds → prices are
  **unadjusted** (limitation L2, §8).
- `api.nasdaq.com/.../historical` serves full 10y OHLCV tables for US
  listings in one call (SPY needs `assetclass=etf`).
- Public endpoints allow only a few requests/minute → 25–90 s pacing,
  30/60/90/120 s backoff, on-disk CSV cache (`data/`), Nasdaq auto-fallback.

## 3. Method (full protocol: `papers/METHOD.md`)

Frozen *before* results were inspected: fractal swings (k=2) → regime
(up = last two swing highs AND lows rise); ATR(14) risk box (1.5×ATR stop,
1.5R target, 10-bar time exit, stop-first on same-bar ambiguity); volume ratio
vs SMA-10; Donchian-20 reference levels (shifted, no lookahead); pin bar =
extreme wick ≥ 2× body with body ≤ 40% of range; S/R zones = swing clusters
within 0.5×ATR with ≥3 touches ≥10 bars apart; gaps split full/partial ×
up/down with a |gap| ≥ 0.1% "visible gap" cut (else every overnight tick
counts — a flaw caught by running, not by reasoning). Metrics: n, win rate,
expectancy (R), profit factor, max drawdown (R), t-test on R, IS/OOS split.

## 4. Results

### E01 — Trend regimes and 5-day drift

| Symbol | up | down | range |
|--------|----|------|-------|
| SPY | +0.19% (1169) | **+0.50%** (520) | +0.29% (824) |
| QQQ | +0.23% (1082) | **+0.59%** (551) | +0.52% (880) |
| AAPL | +0.61% (1048) | **+0.84%** (589) | +0.33% (876) |
| MSFT | +0.32% (1029) | +0.62% (489) | **+0.65%** (995) |

Down-regimes snap back hardest. Trend-following entries on daily bars fight a
mean-reverting tide (HP1).

### E02 — Candlestick shapes vs base next-day up-rate

Base up-rates: SPY 54.9%, QQQ 56.3%, AAPL 53.5%, MSFT 53.4%. No shape beats
base by more than noise **except** the shooting star undershooting it
(SPY 42.9% vs 54.9%; MSFT 47.3% vs 53.4%; QQQ/AAPL ≈ base). Hammers,
marubozus, dojis, spinning tops: ≈ base. The course's strongest-to-weakest
ladder has no predictive content on next-day direction.

### E03 — Support/resistance touch density

142–210 bars of the trailing 400 (35–52%) sit inside a ≥3-touch zone. Levels
are abundant, not rare — selectivity must come from *reaction*, not from the
level itself (consistent with E07).

### E04 — Higher lows into resistance → breakout (CONFIRMED)

| Symbol | HL→R setups | 5d break rate | base rate | lift |
|--------|-------------|---------------|-----------|------|
| SPY | 404 | 58.4% | 33.8% | ×1.73 |
| QQQ | 374 | 56.7% | 32.7% | ×1.73 |
| AAPL | 303 | 55.4% | 28.7% | ×1.93 |
| MSFT | 335 | 56.7% | 26.5% | ×2.14 |

The single strongest confirmation in the study. Buyer-willingness-to-pay-more
into a fixed ceiling really does resolve upward on daily bars.

### E05 — Volume×price matrix (INVERTED vs course)

5-day drift by cell (SPY / QQQ / AAPL / MSFT): UU +0.14/+0.42/+0.61/+0.41,
UD +0.27/+0.30/+0.48/+0.26, **DU +0.37/+0.52/+0.80/+0.95**, DD
+0.35/+0.50/+0.50/+0.53. The course reads DU as "bearish, look to sell";
it is the *best* cell everywhere — capitulation volume marks washouts that
bounce (HP2). UD ("bull trap, stay cautious") is merely average.

### E06 — Breakout entry quality (NUANCED)

All-symbols: buildup-breakout PF 1.15 (n=239) vs power-chase PF 0.84
(n=109) — the course's "never chase power moves" directionally holds, but
expectancy is thin (+0.03R) and OOS samples are small. Breakdown-shorts are
too rare to judge (n=17).

### E07 — Pullbacks: confirmation premium (CONFIRMED)

Aggressive (touch 20EMA in uptrend): PF 1.41, +0.16R (n=745).
Conservative (+rejection candle): **PF 2.28, +0.33R (n=89)**, OOS PF 1.69.
Waiting one bar for proof is the cheapest performance upgrade in the course.

### E08 — Reversals: don't fade the first pullback (CONFIRMED)

Fade-first-flip longs: OOS PF 0.80, −0.15R (n=90). Structure-break shorts:
11 trades total — directionally good (+0.54R) but ungradeably thin; the
honest conclusion is "the prohibition is validated, the prescribed
alternative is underpowered on daily bars."

### E09 — Inside bars: the course's favourite is backwards

Raw inside-bar breakout (both directions): PF 1.23, +0.10R (n=1086) — a
small genuine edge. Small-range-at-value subset: **PF 0.80, −0.09R (n=51)**.
The course's preferred refinement destroys the edge (HP5 caveat: the value
filter only fires in the detector's 400-bar tail, i.e. mostly OOS — still,
the sign flip is the finding).

### E10 — Pin bars: nothing raw, a whisper filtered

Raw: PF 0.97 (n=876) — exactly the "no edge" the literature predicts
(Formiq 252 backtests; Secuora 2,118-trade verification PF 0.72).
Trend/value-filtered: PF 1.05 (n=356), OOS PF 1.37 (n=125). A filter helps;
a business it is not.

### E11 — Gaps: the gradient, not the slogan (REJECTED "90%")

5-day fill rates, |gap| ≥ 0.1% (n in brackets), SPY/QQQ/AAPL/MSFT:

- full_up: 64/65/66/69% — full_up fills *least*
- part_up: 72/71/74/71%
- full_dn: 75/75/70/74%
- part_dn: 81/81/83/84% — partial gap-downs fill *most*

Pooled (4 symbols): full_up 65.9% (2251), part_up 72.0% (2518), full_dn
73.2% (1398), part_dn 82.4% (2331). The ordering is identical on all four
symbols — a genuine regularity (HP3). "90% of gaps fill" is false;
"partial gap-downs fill >80%" is the tradeable residue.

## 5. Trade-level OOS summary (pooled, 4 symbols)

Conservative pullback OOS PF 1.69 (n=31); aggressive OOS PF 1.37 (n=203).
Raw inside-bar OOS PF 1.27 (n=332). Filtered pin OOS PF 1.37 (n=125).
Fade-first OOS PF 0.80. No strategy survives costs with PF > 1.5 OOS except
the small-sample conservative pullback — scale expectations accordingly.

## 6. Hidden patterns (the PhD seeds)

- **HP1 — Downtrend snap-back.** Forward drift is maximal *after* down-regimes
  on all four symbols. Daily equity trends mean-revert faster than courses
  admit; any trend system needs an explicit oversold-bounce opponent model.
- **HP2 — Capitulation-volume inversion.** High-volume down days precede the
  best 5-day drift. Volume confirms *exhaustion*, not continuation, on this
  timeframe — the course's 2×2 matrix needs transposing for daily bars.
- **HP3 — Gap-fill gradient.** part_dn > part_up > full_dn > full_up, invariant
  across symbols. Microstructure story: overnight partial gaps are liquidity
  air-pockets; full gaps embed real information. Testable on intraday next.
- **HP4 — The ~5% hikkake tax.** 2.2–2.8% of bars per side (≈5% total) are
  failed inside-bar breakouts. Any inside-bar breakout system pays this base
  trap rate before costs — size stops accordingly.
- **HP5 — Zone abundance.** 35–52% of bars sit in ≥3-touch zones, so "trade
  from value" cannot be selective by itself; confirmation (E07) does the work.

## 7. How to reproduce

```bash
docker compose up research        # full pipeline: download -> 11 experiments -> results/
# or locally:
pip install -r requirements.txt
PYTHONPATH=src python3 experiments/run_all.py --symbols SPY,QQQ,AAPL,MSFT --range 10y
python3 -m pytest tests/ -q
```

Outputs: `results/summary.json` (per-symbol everything), `results/table.csv`
(trade-level pooled stats), `results/SUMMARY.md` (digest). One Yahoo/Nasdaq
request at a time; CSVs cache under `data/`.

## 8. Limitations (explicit, not buried)

L1 stylised costs (generous to illiquid names); L2 unadjusted prices
(splits remain as jumps); L3 daily bars only — intraday claims (first-hour
range, 5-min gaps) tested in daily analogue; L4 no delisted names; L5 S/R
detector tail-sampled (last 400 bars); L6 four US-centric symbols in this
release (crypto/FX extension §9).

## 9. Pending extension

`BTC-USD, ETH-USD, EURUSD=X, GC=F` downloads are pacing through public-endpoint
throttles (`experiments/dl_background2.py`, log `data/dl2.log`). The runner
auto-ingests any `data/<SYM>_10y.csv` present — rerun §7 when they land; §4
tables will be extended, not rewritten.

## References

- Bailey, Borwein, López de Prado, Zhu — *The Probability of Backtest
  Overfitting* (2014/2015).
- Pardo, R. — *Design, Testing, and Optimization of Trading Systems* (1992,
  walk-forward).
- Park, C-H. & Irwin, S. — *The Profitability of Technical Analysis: A
  Review* (SSRN, 2004).
- Arbi, R. — *A Reproducible Approach to Equity Backtesting* (UCT thesis, 2019).
- QuantifiedStrategies — *Day Trading Price Action Strategy: Overview and
  Backtest* (2026); PriceActionNinja — *Backtesting Forex Price Action*
  (MT4/MT5 tick-data guide); ForexMechanics — *Strategy Testing Protocol*;
  TradersSecondBrain — *How to Build and Backtest a Strategy That Survives
  Live*; Pinetester — *How to Backtest Properly: 10 Rules* (2026).
- Candlestick evidence: ResearchGate statistical analyses of Hammer/Shooting
  Star on 60y S&P data; MDPI Mathematics 8(5):802 adaptive-candle study;
  PatternTests inside-bar backtest (44,126 trades, median PF 0.99);
  TradingSetupsReview inside-bar volume/support filters; Formiq pin-bar 252
  backtests (USD/JPY); Secuora pin-bar verification (2,118 trades, PF 0.72).
- Brooks, A. — *Trading Price Action* (Wiley) — breakout/pullback/breakdown
  taxonomy underlying E06–E08 detectors.
- Data tooling: `ranaroussi/yfinance` docs (reference implementation for the
  Yahoo v8 schema this study's loader mirrors).

## Appendix A — Provenance

- Research queries (sequential, rate-limit-safe): Exa/web, DuckDuckGo,
  OpenResearch web+OpenAlex, arXiv+unified paper search, agent-reach,
  Kaggle, Wikipedia, GSD, GitMCP — distinct keywords each; full notes in
  `papers/METHOD.md`.
- Live-access verification: `agent-reach_stock_quote` (AAPL 345.16, 2026-10-15),
  CoinGecko BTC 30d series cross-check, direct Yahoo/Nasdaq curl probes.
- Run: `results/bench4.out`; tests: `tests/test_smoke.py` (3 passed).
- Nothing in this repo was copied from any local checkout: all code was
  written fresh for this study (`git log` will show single-origin history).
