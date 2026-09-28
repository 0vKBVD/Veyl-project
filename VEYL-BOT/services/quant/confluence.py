from __future__ import annotations


WEIGHTS = {
    "trend": 0.17,
    "momentum": 0.14,
    "structure": 0.16,
    "smart_money": 0.13,
    "volume": 0.12,
    "volatility": 0.10,
    "statistics": 0.08,
    "whales": 0.10,
}


def _clamp(value: float) -> float:
    return max(0, min(100, value))


def calculate_confluence(
    trend: dict,
    momentum: dict,
    structure: dict,
    smart_money: dict,
    volume: dict,
    volatility: dict,
    statistics: dict,
    whales: float = 50,
) -> dict:

    values = {
        "trend": trend.get("score", 50),
        "momentum": momentum.get("score", 50),
        "structure": structure.get("score", 50),
        "smart_money": smart_money.get("score", 50),
        "volume": volume.get("score", 50),
        "volatility": volatility.get("score", 50),
        "statistics": statistics.get("score", 50),
        "whales": whales,
    }

    score = sum(
        values[key] * WEIGHTS[key]
        for key in WEIGHTS
    )

    score = _clamp(score)

    bullish_votes = 0
    bearish_votes = 0

    analyses = [
        trend,
        momentum,
        structure,
        smart_money,
        volume,
    ]

    for analysis in analyses:
        bias = analysis.get("bias")

        if bias == "BULLISH":
            bullish_votes += 1
        elif bias == "BEARISH":
            bearish_votes += 1

    if bullish_votes >= bearish_votes + 2:
        bias = "BULLISH"
    elif bearish_votes >= bullish_votes + 2:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    if score >= 80:
        strength = "VERY HIGH"
    elif score >= 70:
        strength = "HIGH"
    elif score >= 55:
        strength = "MEDIUM"
    elif score >= 40:
        strength = "LOW"
    else:
        strength = "VERY LOW"

    signals = []

    for analysis in analyses:
        signals.extend(analysis.get("signals", []))

    return {
        "score": round(score, 2),
        "bias": bias,
        "strength": strength,
        "bullish_votes": bullish_votes,
        "bearish_votes": bearish_votes,
        "signals": signals,
        "components": values,
    }