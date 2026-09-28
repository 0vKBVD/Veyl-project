from __future__ import annotations

from statistics import mean


def analyze_volatility(candles: list[dict]) -> dict:
    """
    Volatility engine.

    Features:
    - ATR-like range
    - expansion
    - compression
    - volatility regime
    """

    if len(candles) < 15:
        return {
            "score": 50,
            "regime": "NORMAL",
            "signals": [],
        }

    ranges = []

    for candle in candles:
        high = float(candle["high"])
        low = float(candle["low"])

        ranges.append(high - low)

    current_range = ranges[-1]

    short_avg = mean(ranges[-5:])
    long_avg = mean(ranges[-15:])

    if long_avg <= 0:
        ratio = 1
    else:
        ratio = short_avg / long_avg

    score = 50
    signals = []

    if ratio >= 1.5:
        score += 15
        regime = "EXPANSION"
        signals.append("VOLATILITY EXPANSION")
    elif ratio <= 0.65:
        score -= 5
        regime = "COMPRESSION"
        signals.append("VOLATILITY COMPRESSION")
    else:
        regime = "NORMAL"

    if current_range > long_avg * 2:
        signals.append("EXTREME RANGE")

    if current_range < long_avg * 0.5:
        signals.append("LOW RANGE")

    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "regime": regime,
        "ratio": round(ratio, 3),
        "current_range": current_range,
        "signals": signals,
    }