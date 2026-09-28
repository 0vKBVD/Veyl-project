from __future__ import annotations


def _clamp(value: float) -> float:
    return max(0, min(100, value))


def roc(values: list[float], period: int) -> float:
    if len(values) <= period:
        return 0.0

    previous = values[-1 - period]

    if previous == 0:
        return 0.0

    return ((values[-1] - previous) / previous) * 100


def analyze_momentum(candles: list[dict]) -> dict:
    """
    Momentum engine.

    Features:
    - short-term ROC
    - medium-term ROC
    - acceleration
    - exhaustion detection
    """

    if len(candles) < 15:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "acceleration": "NEUTRAL",
            "signals": [],
        }

    closes = [float(c["close"]) for c in candles]

    roc_fast = roc(closes, 5)
    roc_slow = roc(closes, 12)

    previous_fast = 0.0

    if len(closes) > 10:
        old = closes[-6]

        if old != 0:
            previous_fast = ((closes[-6] - closes[-11]) / closes[-11]) * 100

    acceleration = roc_fast - previous_fast

    score = 50
    signals = []

    if roc_fast > 0:
        score += 15
        signals.append("POSITIVE SHORT-TERM MOMENTUM")
    else:
        score -= 15
        signals.append("NEGATIVE SHORT-TERM MOMENTUM")

    if roc_slow > 0:
        score += 15
        signals.append("POSITIVE MEDIUM-TERM MOMENTUM")
    else:
        score -= 15
        signals.append("NEGATIVE MEDIUM-TERM MOMENTUM")

    if acceleration > 0:
        score += 12
        acceleration_state = "ACCELERATING"
        signals.append("MOMENTUM ACCELERATING")
    elif acceleration < 0:
        score -= 12
        acceleration_state = "DECELERATING"
        signals.append("MOMENTUM DECELERATING")
    else:
        acceleration_state = "NEUTRAL"

    # Momentum exhaustion
    if abs(roc_fast) > 15:
        signals.append("POSSIBLE MOMENTUM EXHAUSTION")

    score = _clamp(score)

    if score >= 70:
        bias = "BULLISH"
    elif score <= 30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "score": round(score, 2),
        "bias": bias,
        "acceleration": acceleration_state,
        "roc_fast": round(roc_fast, 4),
        "roc_slow": round(roc_slow, 4),
        "signals": signals,
    }