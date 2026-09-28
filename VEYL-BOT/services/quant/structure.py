from __future__ import annotations


def _pivot_high(values: list[float], index: int, window: int = 2) -> bool:
    if index < window or index >= len(values) - window:
        return False

    current = values[index]

    for i in range(1, window + 1):
        if current <= values[index - i]:
            return False
        if current <= values[index + i]:
            return False

    return True


def _pivot_low(values: list[float], index: int, window: int = 2) -> bool:
    if index < window or index >= len(values) - window:
        return False

    current = values[index]

    for i in range(1, window + 1):
        if current >= values[index - i]:
            return False
        if current >= values[index + i]:
            return False

    return True


def analyze_structure(candles: list[dict]) -> dict:
    """
    Market structure engine.

    Detects:
    - HH
    - HL
    - LH
    - LL
    - approximate BOS
    - structure bias
    """

    if len(candles) < 10:
        return {
            "score": 50,
            "bias": "NEUTRAL",
            "structure": "UNKNOWN",
            "signals": [],
        }

    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    close = float(candles[-1]["close"])

    pivot_highs = []
    pivot_lows = []

    for i in range(2, len(candles) - 2):
        if _pivot_high(highs, i):
            pivot_highs.append((i, highs[i]))

        if _pivot_low(lows, i):
            pivot_lows.append((i, lows[i]))

    signals = []
    score = 50

    labels = []

    if len(pivot_highs) >= 2:
        previous = pivot_highs[-2][1]
        latest = pivot_highs[-1][1]

        if latest > previous:
            labels.append("HH")
            score += 15
            signals.append("HIGHER HIGH")
        else:
            labels.append("LH")
            score -= 10
            signals.append("LOWER HIGH")

    if len(pivot_lows) >= 2:
        previous = pivot_lows[-2][1]
        latest = pivot_lows[-1][1]

        if latest > previous:
            labels.append("HL")
            score += 15
            signals.append("HIGHER LOW")
        else:
            labels.append("LL")
            score -= 15
            signals.append("LOWER LOW")

    if pivot_highs:
        last_high = pivot_highs[-1][1]

        if close > last_high:
            score += 15
            signals.append("BULLISH BOS")

    if pivot_lows:
        last_low = pivot_lows[-1][1]

        if close < last_low:
            score -= 15
            signals.append("BEARISH BOS")

    score = max(0, min(100, score))

    if score >= 70:
        bias = "BULLISH"
    elif score <= 30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    if "HH" in labels and "HL" in labels:
        structure = "BULLISH STRUCTURE"
    elif "LH" in labels and "LL" in labels:
        structure = "BEARISH STRUCTURE"
    else:
        structure = "MIXED STRUCTURE"

    return {
        "score": round(score, 2),
        "bias": bias,
        "structure": structure,
        "labels": labels,
        "signals": signals,
        "last_high": pivot_highs[-1][1] if pivot_highs else None,
        "last_low": pivot_lows[-1][1] if pivot_lows else None,
    }