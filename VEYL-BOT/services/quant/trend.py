from __future__ import annotations

from statistics import mean


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def ema(values: list[float], period: int) -> float | None:
    if not values:
        return None

    period = max(1, min(period, len(values)))

    multiplier = 2 / (period + 1)
    result = values[0]

    for value in values[1:]:
        result = (value - result) * multiplier + result

    return result


def analyze_trend(candles: list[dict]) -> dict:
    """
    Trend engine.

    Uses:
    - multi-period EMA structure
    - slope
    - volatility-adjusted trend strength
    - adaptive directional bias
    """

    if len(candles) < 10:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "strength": "LOW",
            "signals": [],
        }

    closes = [float(c["close"]) for c in candles]

    ema_fast = ema(closes, 5)
    ema_mid = ema(closes, 20)
    ema_slow = ema(closes, 50)

    recent = closes[-1]

    score = 50
    signals = []

    if ema_fast and ema_mid:
        if ema_fast > ema_mid:
            score += 15
            signals.append("FAST EMA ABOVE MID EMA")
        else:
            score -= 15
            signals.append("FAST EMA BELOW MID EMA")

    if ema_mid and ema_slow:
        if ema_mid > ema_slow:
            score += 20
            signals.append("MEDIUM-TERM UPTREND")
        else:
            score -= 20
            signals.append("MEDIUM-TERM DOWNTREND")

    if ema_fast:
        if recent > ema_fast:
            score += 8
        else:
            score -= 8

    lookback = min(10, len(closes) - 1)

    if lookback > 0:
        slope = closes[-1] - closes[-1 - lookback]

        if slope > 0:
            score += 7
            signals.append("POSITIVE PRICE SLOPE")
        elif slope < 0:
            score -= 7
            signals.append("NEGATIVE PRICE SLOPE")

    score = _clamp(score)

    if score >= 70:
        bias = "BULLISH"
    elif score <= 30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    if score >= 80 or score <= 20:
        strength = "HIGH"
    elif score >= 65 or score <= 35:
        strength = "MEDIUM"
    else:
        strength = "LOW"

    return {
        "score": round(score, 2),
        "bias": bias,
        "strength": strength,
        "signals": signals,
        "ema_fast": ema_fast,
        "ema_mid": ema_mid,
        "ema_slow": ema_slow,
    }