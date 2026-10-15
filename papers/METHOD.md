# Method Protocol: Verifying Discretionary Price-Action Claims on Live Market Data

**Study:** `price-action-zero-to-hero-live-benchmark-2026`
**Question:** Which claims from a popularYouTube-style "price action zero-to-hero"
course (trend structure, candlesticks, support/resistance, volume, breakouts,
fakeouts, pullbacks, reversals, inside bars, pin bars, gaps) survive mechanical,
costed backtesting on live public market data?
**Date:** 2026-10-15. **Data:** daily OHLCV, Yahoo Finance v8 + Nasdaq fallback.

## 1. Why this protocol (online best-practice synthesis, Oct 2026)

Sequential web research (one query at a time to respect rate limits) across
Exa/web, DuckDuckGo, OpenResearch (web + OpenAlex), arXiv/Semantic/Crossref,
agent-reach, Kaggle, Wikipedia, GSD and GitMCP docs converged on one consensus:

1. **Quantify first.** Discretionary rules ("buy the breakout") must be frozen
   into objective, code-checkable rules before any test (ForexMechanics
   testing protocol v1; TradersSecondBrain build-and-backtest guide).
   A 10-year-old must be able to apply the rule.
2. **Costs are part of the edge.** Commission + spread/slippage on *every* fill;
   Pine default 0 costs are "dangerously misleading" (TradingView docs via
   Pinetester). We charge 5 bp commission + 2 bp slippage per side.
3. **Separate development from evaluation.** 70% in-sample / 30% out-of-sample
   chronological split; OOS tested once; once inspected, OOS becomes in-sample
   (Bailey et al. 2014, Probability of Backtest Overfitting; Pardo 1992
   walk-forward).
4. **Demand enough trades + uncertainty.** No magic "100-trade" gate; report n,
   win rate, profit factor, expectancy in R, max drawdown, and a t-test on R.
5. **No lookahead.** Signal at close *t* executes at open *t+1*; Donchian levels
   shifted; same-bar stop+target ambiguity resolved conservatively (stop first).
6. **Baselines & regimes.** Compare against buy-and-hold; tag regimes
   (up/down/range); test multiple assets and the same settings un-retuned.
7. **Log everything.** Every variant tried is a degree of freedom; we log all
   experiments including failures (reproducibility thesis, Arbi 2019).

## 2. Claim -> mechanical rule mapping (E01..E11)

| ID | Course claim | Mechanical rule (frozen before test) |
|----|--------------|--------------------------------------|
| E01 | HH+HL=uptrend, LH+LL=downtrend; slope+duration=strength | Fractal swings (k=2); regime=up iff last 2 swing highs AND lows rise; fwd-5d drift by regime |
| E02 | marubozu strongest, then pin bars, then spinning/doji weakest | Shape-only detectors (body/range/wick ratios); next-day up-rate per shape |
| E03 | >=3 touches spaced in time = major level; levels are zones | Swing cluster within 0.5*ATR, >=3 touches >=10 bars apart; zone=mid+/-0.5ATR |
| E04 | Higher lows into resistance -> break; power move + rejection -> reversal | HL-into-R detector vs 5d breakout rate; power=rng>1.5ATR |
| E05 | UU bullish, UD bull-trap, DU bearish, DD bear-trap | vol_ratio=vol/SMA10 <> 1.0; fwd-5d by cell |
| E06 | Trade buildup breakouts, never chase power moves | Donchian-20 break x (range-contracted buildup vs power-move); 1.5R/1.5ATR |
| E07 | Pullbacks: aggressive=touch, conservative=rejection candle | 20EMA touch in uptrend vs touch+hammer/marubozu; next-open entry |
| E08 | Never fade first pullback; trade break-of-structure reversals | Fade-first-flip vs structure-break+rejection-candle short |
| E09 | Small-range inside bars at value; beware hikkake traps | IB raw vs small-range+value; hikkake trap frequency |
| E10 | Pin bars (wick>=2x body) only with trend / at value | Raw pin vs trend/value-filtered; 1.5R/1.5ATR |
| E11 | 90% of gaps fill; full gaps continue on volume | Fill-within-5d rate by gap type; full-gap+high-vol continuation trades |

Trade engine: stop = 1.5*ATR(14), target = 1.5R, 10-bar time exit.
RSI(14) convergence recorded as a diagnostic filter for E06.

## 3. Limitations (explicit)

- **L1 costs are stylised.** 7 bp/side approximates liquid US equities; BTC and
  GC=F are costlier -- our costs are therefore *generous* to the strategies.
- **L2 unadjusted prices.** The `events=div,split` Yahoo parameter triggered
  HTTP 429 from our egress (verified by A/B curl tests), so corporate-action
  jumps (notably AAPL/MSFT splits) remain in-sample as noise; disclosed, not hidden.
- **L3 daily bars only.** Intraday claims (5-min gaps, first-hour range) are
  tested in daily analogue; intraday replication is listed as future work.
- **L4 no survivorship correction.** Universe = 8 liquid symbols chosen ex-ante
  (SPY, QQQ, AAPL, MSFT, BTC-USD, ETH-USD, EURUSD=X, GC=F); no delisted names.
- **L5 S/R detector bounded.** Zone clustering runs on trailing 252-bar window
  over the last 400 bars (compute), so E03/E09-value are tail-sampled.
