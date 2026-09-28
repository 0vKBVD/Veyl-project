from __future__ import annotations

from statistics import mean, pstdev


def analyze_volume(candles: list[dict]) -> dict:
    """
    Volume engine.

    Features:
    - relative volume
    - volume anomaly
    - directional volume pressure
    - volume efficiency
    """

    if len(candles) < 10:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "signals": [],
            "rvol": 1.0,
        }

    volumes = [float(c.get("volume", 0) or 0) for c in candles]

    current_volume = volumes[-1]
    baseline_values = volumes[-11:-1]

    baseline = mean(baseline_values) if baseline_values else 0

    if baseline <= 0:
        rvol = 1.0
    else:
        rvol = current_volume / baseline

    score = 50
    signals = []

    if rvol >= 2:
        score += 20
        signals.append("VERY HIGH RVOL")
    elif rvol >= 1.3:
        score += 10
        signals.append("HIGH RVOL")
    elif rvol < 0.7:
        score -= 8
        signals.append("LOW RELATIVE VOLUME")

    # Directional pressure
    bullish_volume = 0.0
    bearish_volume = 0.0

    for candle in candles[-10:]:
        volume = float(candle.get("volume", 0) or 0)
        open_price = float(candle["open"])
        close_price = float(candle["close"])

        if close_price >= open_price:
            bullish_volume += volume
        else:
            bearish_volume += volume

    total = bullish_volume + bearish_volume

    if total > 0:
        pressure = bullish_volume / total

        if pressure >= 0.65:
            score += 15
            signals.append("STRONG BUY VOLUME PRESSURE")
        elif pressure <= 0.35:
            score -= 15
            signals.append("STRONG SELL VOLUME PRESSURE")

    # Anomaly detection
    if len(volumes) >= 10:
        avg = mean(volumes[:-1])
        std = pstdev(volumes[:-1]) if len(volumes[:-1]) > 1 else 0

        if std > 0 and current_volume > avg + 2 * std:
            signals.append("VOLUME ANOMALY")

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
        "rvol": round(rvol, 3),
        "bullish_volume": bullish_volume,
        "bearish_volume": bearish_volume,
        "signals": signals,
    }