# File: Super-trading-bot-V3.py
"""
Super-trading-bot-V3
Strategy: Donchian-style channel breakout with ATR-based stop-loss / take-profit.

Core idea
---------
- Use channel breakout (highest high / lowest low over N bars) to detect strong moves.
- Use ATR to size stop-loss and take-profit in volatility units.

Trading rules
-------------
Entry:
    • BUY  when close > highest(high, channel_period)
    • SELL when close < lowest(low,  channel_period)

Exit (for both long and short):
    • Close trade when unrealised profit >= atr_tp * ATR
    • or when unrealised loss   >= atr_sl * ATR

Notes:
    • This is a very minimal backtester, no commissions / slippage, 1-unit position.
"""

from typing import List, Literal, Union, Optional

Price = Union[float, int]
Signal = Literal["BUY", "SELL", "FLAT"]


def _nan() -> float:
    """Helper to create a NaN value."""
    return float("nan")


def _is_nan(x: float) -> bool:
    """NaN check without importing math (NaN != NaN)."""
    return x != x


def true_range(high: List[Price], low: List[Price], close: List[Price]) -> List[float]:
    """
    True Range (TR) series.

    TR[i] = max(
        high[i] - low[i],
        abs(high[i] - close[i-1]),
        abs(low[i]  - close[i-1]),
    )
    """
    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have the same length")

    tr: List[float] = []

    for i in range(len(close)):
        h = float(high[i])
        l = float(low[i])
        c_prev = float(close[i - 1]) if i > 0 else float(close[i])
        tr.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))

    return tr


def atr(
    high: List[Price],
    low: List[Price],
    close: List[Price],
    period: int = 14,
) -> List[float]:
    """
    Average True Range (Wilder's ATR).

    :param high: high prices
    :param low: low prices
    :param close: close prices
    :param period: ATR lookback length
    :return: ATR series (NaN for warm-up bars)
    """
    if period <= 0:
        raise ValueError("ATR period must be > 0")

    tr = true_range(high, low, close)
    atr_values: List[float] = []
    running_sum = 0.0

    for i, v in enumerate(tr):
        running_sum += v

        if i < period - 1:
            # Not enough data for initial ATR
            atr_values.append(_nan())
            continue

        if i == period - 1:
            # First ATR value: simple average of first 'period' TRs
            atr_values.append(running_sum / period)
        else:
            # Wilder's smoothing
            prev = atr_values[-1]
            atr_values.append((prev * (period - 1) + v) / period)

    return atr_values


def highest(values: List[Price], period: int) -> List[float]:
    """
    Highest value over a rolling window.

    :param values: input data (e.g. highs)
    :param period: lookback length
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    out: List[float] = []
    for i in range(len(values)):
        if i + 1 < period:
            out.append(_nan())
        else:
            window = [float(x) for x in values[i + 1 - period : i + 1]]
            out.append(max(window))
    return out


def lowest(values: List[Price], period: int) -> List[float]:
    """
    Lowest value over a rolling window.

    :param values: input data (e.g. lows)
    :param period: lookback length
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    out: List[float] = []
    for i in range(len(values)):
        if i + 1 < period:
            out.append(_nan())
        else:
            window = [float(x) for x in values[i + 1 - period : i + 1]]
            out.append(min(window))
    return out


def generate_signals(
    high: List[Price],
    low: List[Price],
    close: List[Price],
    channel_period: int = 20,
) -> List[Signal]:
    """
    Generate BUY/SELL/FLAT breakout signals.

    :param high: high prices
    :param low: low prices
    :param close: close prices
    :param channel_period: lookback for highest/lowest channel
    """
    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have the same length")

    hi = highest(high, channel_period)
    lo = lowest(low, channel_period)

    signals: List[Signal] = []

    for h, l, c in zip(hi, lo, close):
        if _is_nan(h) or _is_nan(l):
            signals.append("FLAT")
            continue

        c = float(c)

        if c > h:
            signals.append("BUY")
        elif c < l:
            signals.append("SELL")
        else:
            signals.append("FLAT")

    return signals


def backtest(
    high: List[Price],
    low: List[Price],
    close: List[Price],
    channel_period: int = 20,
    atr_period: int = 14,
    atr_tp: float = 3.0,
    atr_sl: float = 1.5,
) -> float:
    """
    Minimal breakout + ATR stop backtest.

    Position logic:
        - At most one position at a time.
        - Enter long/short on breakout.
        - Exit on ATR-based TP/SL.

    Returns:
        Total PnL in price points (1-unit positions).
    """
    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have the same length")

    signals = generate_signals(high, low, close, channel_period)
    atr_values = atr(high, low, close, atr_period)

    position = 0  # 0=flat, 1=long, -1=short
    entry_price: Optional[float] = None
    pnl = 0.0

    for i in range(len(close)):
        c = float(close[i])
        sig = signals[i]
        a = atr_values[i]

        if _is_nan(a):
            # ATR not ready yet
            continue

        if position == 0:
            # Look for new entries
            if sig == "BUY":
                position = 1
                entry_price = c
            elif sig == "SELL":
                position = -1
                entry_price = c
        else:
            # Manage open trade
            if entry_price is None:
                # Safety check – should not happen
                position = 0
                continue

            distance = c - entry_price  # positive if price > entry

            if position == 1:
                # Long: TP when distance >= atr_tp * ATR, SL when distance <= -atr_sl * ATR
                if distance >= atr_tp * a or distance <= -atr_sl * a:
                    pnl += distance
                    position = 0
                    entry_price = None

            elif position == -1:
                # Short: profit if price goes down (distance negative)
                # Convert to "short distance" in our favour
                short_distance = -distance
                if short_distance >= atr_tp * a or short_distance <= -atr_sl * a:
                    pnl += short_distance
                    position = 0
                    entry_price = None

    # Force close last position at final price (optional behaviour)
    if position != 0 and entry_price is not None:
        last = float(close[-1])
        pnl += (last - entry_price) * position

    return pnl


if _name_ == "_main_":
    # Dummy OHLC data for quick check
    close = [100 + (i % 10) for i in range(200)]
    high = [c + 1 for c in close]
    low = [c - 1 for c in close]
    print("V3 PnL:", backtest(high, low, close))
