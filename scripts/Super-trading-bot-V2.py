# File: Super-trading-bot-V2.py
"""
Super-trading-bot-V2
Strategy: SMA crossover + RSI filter

Logic:
- Core signal: fast SMA vs slow SMA crossover
- Filter: RSI must be below/above given thresholds

Default behaviour:
- BUY  when fast SMA crosses above slow SMA AND RSI < 70
- SELL when fast SMA crosses below slow SMA AND RSI > 30

Notes:
- You can adjust rsi_buy_limit / rsi_sell_limit to be more conservative
  (e.g. BUY only when RSI < 60, SELL only when RSI > 40).
"""

from typing import List, Literal, Union, Optional

Price = Union[float, int]
Signal = Literal["BUY", "SELL", "FLAT"]


def _nan() -> float:
    """Return a NaN value (helper to avoid repeating float('nan'))."""
    return float("nan")


def sma(prices: List[Price], period: int) -> List[float]:
    """
    Simple Moving Average.

    :param prices: list of price values
    :param period: lookback length
    :return: list of SMA values (NaN for the first period-1 entries)
    """
    if period <= 0:
        raise ValueError("SMA period must be > 0")

    window_sum = 0.0
    values: List[float] = []

    for i, p in enumerate(prices):
        window_sum += float(p)
        if i >= period:
            window_sum -= float(prices[i - period])

        if i + 1 >= period:
            values.append(window_sum / period)
        else:
            values.append(_nan())

    return values


def rsi(prices: List[Price], period: int = 14) -> List[float]:
    """
    Very simple RSI implementation (closing-price based).

    :param prices: list of price values
    :param period: lookback length (default 14)
    :return: list of RSI values between 0 and 100 (NaN for warm-up bars)
    """
    if period <= 0:
        raise ValueError("RSI period must be > 0")

    if len(prices) < 2:
        # Not enough data to compute changes
        return [_nan() for _ in prices]

    # Price changes
    gains: List[float] = [0.0]
    losses: List[float] = [0.0]

    for i in range(1, len(prices)):
        change = float(prices[i]) - float(prices[i - 1])
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain: List[float] = []
    avg_loss: List[float] = []
    rsi_values: List[float] = []

    gain_sum = 0.0
    loss_sum = 0.0

    for i in range(len(prices)):
        if i == 0:
            # First bar: no RSI
            avg_gain.append(_nan())
            avg_loss.append(_nan())
            rsi_values.append(_nan())
            continue

        gain_sum += gains[i]
        loss_sum += losses[i]

        # Warm-up: no RSI until enough data
        if i < period:
            avg_gain.append(_nan())
            avg_loss.append(_nan())
            rsi_values.append(_nan())
            continue

        # Initial averages at i == period
        if i == period:
            avg_gain_value = gain_sum / period
            avg_loss_value = loss_sum / period
        else:
            # Wilder's smoothing
            prev_avg_gain = avg_gain[-1]
            prev_avg_loss = avg_loss[-1]
            avg_gain_value = (prev_avg_gain * (period - 1) + gains[i]) / period
            avg_loss_value = (prev_avg_loss * (period - 1) + losses[i]) / period

        avg_gain.append(avg_gain_value)
        avg_loss.append(avg_loss_value)

        if avg_loss_value == 0:
            rsi_values.append(100.0)  # no losses -> RSI at 100
        else:
            rs = avg_gain_value / avg_loss_value
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_values


def _is_nan(x: float) -> bool:
    """Check NaN without importing math (NaN != NaN)."""
    return x != x


def generate_signals(
    prices: List[Price],
    fast_period: int = 10,
    slow_period: int = 30,
    rsi_period: int = 14,
    rsi_buy_limit: float = 70.0,
    rsi_sell_limit: float = 30.0,
) -> List[Signal]:
    """
    Generate BUY/SELL/FLAT signals from SMA crossovers filtered by RSI.

    :param prices: list of closing prices
    :param fast_period: fast SMA length
    :param slow_period: slow SMA length (should be > fast_period)
    :param rsi_period: RSI lookback
    :param rsi_buy_limit: maximum RSI value allowed to BUY (default 70)
    :param rsi_sell_limit: minimum RSI value required to SELL (default 30)
    :return: list of trading signals
    """
    if slow_period <= fast_period:
        raise ValueError("slow_period should be strictly greater than fast_period")

    fast = sma(prices, fast_period)
    slow = sma(prices, slow_period)
    rsi_values = rsi(prices, rsi_period)

    signals: List[Signal] = []
    prev_fast_above: Optional[bool] = None

    for f, s, r in zip(fast, slow, rsi_values):
        # Skip bars where any indicator is not ready (NaN)
        if _is_nan(f) or _is_nan(s) or _is_nan(r):
            signals.append("FLAT")
            continue

        fast_above = f > s

        if prev_fast_above is None:
            # First bar with valid data: no signal yet
            signals.append("FLAT")
        elif not prev_fast_above and fast_above and r < rsi_buy_limit:
            # Bullish crossover + RSI under threshold -> BUY
            signals.append("BUY")
        elif prev_fast_above and not fast_above and r > rsi_sell_limit:
            # Bearish crossover + RSI above threshold -> SELL
            signals.append("SELL")
        else:
            signals.append("FLAT")

        prev_fast_above = fast_above

    return signals


def backtest(prices: List[Price], **params) -> float:
    """
    Minimalistic backtest engine.

    Rules:
    - Enter long on BUY signal if flat.
    - Exit long on SELL signal.
    - No short selling, no commissions, 1 unit position.

    :param prices: list of prices
    :param params: forwarded to generate_signals()
    :return: total PnL in price points
    """
    signals = generate_signals(prices, **params)
    position = 0  # 0 = flat, 1 = long
    entry_price: Optional[float] = None
    pnl = 0.0

    for i in range(1, len(prices)):
        sig = signals[i]
        price = float(prices[i])

        if sig == "BUY" and position == 0:
            # Open long
            position = 1
            entry_price = price

        elif sig == "SELL" and position == 1 and entry_price is not None:
            # Close long
            pnl += price - entry_price
            position = 0
            entry_price = None

    # Close any open position at last price
    if position == 1 and entry_price is not None:
        pnl += float(prices[-1]) - entry_price

    return pnl


if _name_ == "_main_":
    # Quick sanity check with dummy data
    sample_prices = [100 + (i % 7) - 3 for i in range(200)]
    pnl = backtest(sample_prices)
    print("V2 PnL:", pnl)
