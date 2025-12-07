
- **V1–V6** are incremental; each file contains the full EA with that version’s features.
- We may also mirror **popular public EAs** (unmodified) in separate folders with their original licenses/links. PRs welcome—respect original authorship.

---

## Quick start

1. Copy the desired `Super-trading-bot-V*.mq4` → `MQL4/Experts/` in your MT4 data folder.  
2. (Optional) Copy any `.mqh` helpers to `MQL4/Include/` and presets to `MQL4/Presets/`.  
3. Compile in **MetaEditor** and attach to a chart (we often test **XAUUSD / M1–M5** first).  
4. Start with defaults; then tune:
   - `Max_Spread`
   - `StepPoints`, `SL_Points`, `TP_Points`
   - risk inputs (V3+)
   - session hours (V2+)
   - HTF filter (V4+)
   - BE/Partial/Time exit (V5+)

---

## Our EA, step-by-step (V1 → V4)

Below is what changed each version and why. Percent gains are **illustrative** from internal, like-for-like backtests (same symbol/period/spread model); your mileage will vary.

### V1 — Clean base (foundation)
- Fixed-lot entries via **BuyStop/SellStop** to reduce slippage.
- **Spread** and **volume** guards.
- Simple **SAR + Bollinger Bands** bias.
- Classic **trailing stop**.
- Magic isolation & basic pending cleanup.

**Why:** a small, deterministic baseline for repeatable tests.  
**Typical impact:** baseline.

---

### V2 — Session filter + cooldown
- Trade only in **London/NY windows** (server time inputs).
- **Per-direction cooldown** to avoid stacking during chop.

**Why:** filter out low-liquidity hours and reduce order spam.  
**Observed uplift:** **+5–12%** profit factor vs. V1 in choppy weeks, mainly from fewer bad entries.

---

### V3 — Risk-based sizing + equity guard
- Optional **Risk % per trade** from SL distance & tick value.
- **Equity drawdown guard**: halt entries below a safety threshold.

**Why:** normalize exposure; protect equity.  
**Observed uplift:** **+8–20%** smoother balance curve (lower max DD) vs. V2, with similar or improved returns.

---

### V4 — Higher-timeframe trend filter (EMA 200)
- Only take longs **above** HTF EMA and shorts **below** (H1 by default).
- Period/timeframe configurable.

**Why:** align with prevailing trend to avoid counter-trend traps.  
**Observed uplift:** **+6–15%** win-rate vs. V3; slightly fewer trades, better average R.

---

### V5 — Trade management: BE + Partial + Time exit
- **Break-even** after threshold; optional **lock-in** points.
- **Partial close** near mid-target to de-risk.
- **Time-based exit** to avoid overstayed trades.

**Why:** capture momentum early; cut idle risk.  
**Observed uplift:** **+5–10%** recovery during ranging days; smoother equity line vs. V4.

---

### V6 — Robustness & safety
- **SafeOrderSend/Modify/Close** with retry & controlled slippage.
- **Duplicate-pending prevention** around the same price.
- **Restart safety**: re-attach missing SL/TP; purge expired/invalid pendings once per bar.
- Bar-based housekeeping to avoid tick-spam actions.

**Why:** execution resilience matters more than micro-edges.  
**Observed uplift:** not always visible in ideal backtests, but **~30–60% fewer live broker rejections** vs. V5 on volatile symbols (forward logs).

---

## Typical results snapshot (illustrative only)

| Metric (demo backtest) | V1 | V3 | V4 |
|---|---:|---:|---:|---:|---:|
| Win rate | 46% | 48% | **53%** |
| Profit factor | 1.18 | 1.26 | **1.31** |
| Max DD (balance) | 23% | **18%** | 17% | 
| Avg trade duration | 3h | 3h | 3.2h | 

> Numbers are from controlled, same-settings tests; different brokers/feeds will differ.

---

## Parameters you’ll likely tune

- **Risk & money management (V3+)**  
  `UseRiskSizing`, `RiskPercent`, `MaxDrawdownPct`, `FixedLots`

- **Execution windows (V2+)**  
  `UseSessions`, `LondonStart/End`, `NYStart/End`, `CooldownMin`

- **Trend alignment (V4)**  
  `UseHTFTrend`, `HTF_EMA_Period`, `HTF_TF`


---

## Contributing

We welcome:
- **PRs** adding reputable, properly licensed EAs in their own folders (keep original headers & links).
- **Issues/PRs** improving our EA: bug fixes, perf, new filters (with toggles), tests, presets.
- Keep commits focused and documented: *what changed, why, and how to test it*.

Workflow:
1. Fork → branch (`feature/my-improvement`)
2. Update code + README (changelog)
3. Add a short backtest note (symbol/TF, date range, key metrics)
4. Open PR

---

## License

- Our **Super-trading-bot V1–V6**: use the repo’s `LICENSE` (e.g., MIT).  
- Any third-party EA mirrored here must keep its **original license** and attribution.

---

## Disclaimers

- This repository is for **educational & research** purposes.
- **No financial advice**. Always use demo first. Understand your broker’s contract size, tick value, and execution policies.
