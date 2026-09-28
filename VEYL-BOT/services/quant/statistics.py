from __future__ import annotations

from statistics import mean, pstdev


def analyze_statistics(candles: list[dict]) -> dict:
    """
    Statistical valuation engine.

    Features:
    - rolling mean
    - standard deviation
    - z-score
    - statistical stretch
    - mean-reversion pressure
    """

    if len(candles) < 20:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "signals": [],
        }

    closes = [float(c["close"]) for c in candles]

    window = closes[-20:]

    fair_value = mean(window)
    deviation = pstdev(window)

    if deviation <= 0:
        z_score = 0
    else:
        z_score = (closes[-1] - fair_value) / deviation

    score = 50
    signals = []

    if z_score > 2:
        score -= 15
        signals.append("STATISTICALLY OVEREXTENDED")
    elif z_score > 1:
        score -= 5
        signals.append("ABOVE FAIR VALUE")
    elif z_score < -2:
        score += 15
        signals.append("STATISTICALLY UNDERVALUED")
    elif z_score < -1:
        score += 5
        signals.append("BELOW FAIR VALUE")
    else:
        signals.append("NEAR STATISTICAL FAIR VALUE")

    if z_score > 0.5:
        bias = "ABOVE_VALUE"
    elif z_score < -0.5:
        bias = "BELOW_VALUE"
    else:
        bias = "FAIR_VALUE"

    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "bias": bias,
        "fair_value": fair_value,
        "std_dev": deviation,
        "z_score": round(z_score, 3),
        "signals": signals,
    }