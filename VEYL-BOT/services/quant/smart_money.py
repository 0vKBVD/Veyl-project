from __future__ import annotations


def analyze_smart_money(candles: list[dict]) -> dict:
    """
    Original simplified Smart Money-style analysis.

    Detects:
    - displacement candles
    - liquidity sweeps
    - imbalance/FVG-like gaps
    - impulse conditions
    """

    if len(candles) < 8:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "signals": [],
        }

    score = 50
    signals = []

    current = candles[-1]
    previous = candles[-2]

    current_open = float(current["open"])
    current_close = float(current["close"])
    current_high = float(current["high"])
    current_low = float(current["low"])

    prev_high = float(previous["high"])
    prev_low = float(previous["low"])

    candle_range = current_high - current_low

    if candle_range <= 0:
        candle_range = 1e-9

    body = abs(current_close - current_open)
    body_ratio = body / candle_range

    # Strong displacement
    if body_ratio >= 0.70:
        if current_close > current_open:
            score += 18
            signals.append("BULLISH DISPLACEMENT")
        else:
            score -= 18
            signals.append("BEARISH DISPLACEMENT")

    # Liquidity sweep
    if current_low < prev_low and current_close > prev_low:
        score += 10
        signals.append("SELL-SIDE LIQUIDITY SWEEP")

    if current_high > prev_high and current_close < prev_high:
        score -= 10
        signals.append("BUY-SIDE LIQUIDITY SWEEP")

    # Simple imbalance approximation
    if len(candles) >= 3:
        first = candles[-3]
        middle = candles[-2]
        last = candles[-1]

        first_high = float(first["high"])
        first_low = float(first["low"])

        last_high = float(last["high"])
        last_low = float(last["low"])

        if first_high < last_low:
            score += 8
            signals.append("BULLISH IMBALANCE")

        if first_low > last_high:
            score -= 8
            signals.append("BEARISH IMBALANCE")

    # Strong impulse
    if body_ratio >= 0.80:
        signals.append("IMPULSE CANDLE")

    score = max(0, min(100, score))

    if score >= 70:
        bias = "BULLISH"
    elif score <= 30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "score": round(score, 2),
        "bias": bias,
        "signals": signals,
    }