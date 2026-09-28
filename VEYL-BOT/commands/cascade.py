import asyncio
import time
from collections import deque
from statistics import mean, pstdev
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# VEYL / CASCADE PRO
# ============================================================
#
# Multi-factor Futures cascade detector.
#
# DATA:
#   • Binance USDⓈ-M Futures 1m klines
#   • Open Interest
#   • Funding Rate
#   • Taker Buy / Sell volume
#   • Forced liquidation orders
#
# IMPORTANT:
# This engine detects MARKET CONDITIONS associated with
# liquidation cascades. It does not claim that every strong
# move is a liquidation event.
#
# ============================================================


# ============================================================
# BINANCE FUTURES API
# ============================================================

FUTURES_BASE_URL = "https://fapi.binance.com"

KLINES_URL = f"{FUTURES_BASE_URL}/fapi/v1/klines"
OPEN_INTEREST_URL = f"{FUTURES_BASE_URL}/fapi/v1/openInterest"
FUNDING_URL = f"{FUTURES_BASE_URL}/fapi/v1/fundingRate"
PREMIUM_URL = f"{FUTURES_BASE_URL}/fapi/v1/premiumIndex"

TAKER_VOLUME_URL = (
    f"{FUTURES_BASE_URL}/futures/data/takerBuySellVol"
)

FORCE_ORDERS_URL = (
    f"{FUTURES_BASE_URL}/fapi/v1/forceOrders"
)


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 12

INTERVAL = "1m"
CANDLE_LIMIT = 60

OI_HISTORY_LIMIT = 20

LIQUIDATION_LOOKBACK_MS = 5 * 60 * 1000

VOLUME_BASELINE = 20
VOLATILITY_BASELINE = 20
MOMENTUM_BASELINE = 10


# ============================================================
# THRESHOLDS
# ============================================================

VOLUME_SPIKE_THRESHOLD = 1.8
VOLATILITY_SPIKE_THRESHOLD = 1.6
MOMENTUM_SPIKE_THRESHOLD = 1.6

OI_CHANGE_THRESHOLD = 0.003

TAKER_IMBALANCE_THRESHOLD = 0.12

LIQUIDATION_CONFIRMATION_USD = 25_000


# ============================================================
# VEYL COLORS
# ============================================================

VEYL_WHITE = 0xF2F2F2
VEYL_GREY = 0x8A8A8A
VEYL_DARK = 0x111111


# ============================================================
# ASSET MAP
# ============================================================

ASSET_MAP = {

    "btc": "BTCUSDT",
    "bitcoin": "BTCUSDT",

    "eth": "ETHUSDT",
    "ethereum": "ETHUSDT",

    "sol": "SOLUSDT",
    "solana": "SOLUSDT",

    "bnb": "BNBUSDT",

    "xrp": "XRPUSDT",

    "doge": "DOGEUSDT",
    "dogecoin": "DOGEUSDT",

    "ada": "ADAUSDT",
    "cardano": "ADAUSDT",

    "avax": "AVAXUSDT",
    "avalanche": "AVAXUSDT",

    "link": "LINKUSDT",
    "chainlink": "LINKUSDT",

    "sui": "SUIUSDT",

    "ton": "TONUSDT",
    "toncoin": "TONUSDT",

    "trx": "TRXUSDT",

    "dot": "DOTUSDT",
    "polkadot": "DOTUSDT",

    "matic": "POLUSDT",
    "pol": "POLUSDT",

    "shib": "SHIBUSDT",
    "shiba": "SHIBUSDT",

    "atom": "ATOMUSDT",
    "cosmos": "ATOMUSDT",

    "ltc": "LTCUSDT",
    "litecoin": "LTCUSDT",

    "uni": "UNIUSDT",
    "uniswap": "UNIUSDT",
}


# ============================================================
# HTTP SESSION
# ============================================================

_session: Optional[aiohttp.ClientSession] = None


async def get_session():

    global _session

    if _session is None or _session.closed:

        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT
        )

        _session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "VEYL-Cascade-Pro/2.0",
                "Accept": "application/json",
            },
        )

    return _session


# ============================================================
# HTTP GET HELPER
# ============================================================

async def api_get(url, params=None):

    session = await get_session()

    try:

        async with session.get(
            url,
            params=params,
        ) as response:

            if response.status != 200:

                text = await response.text()

                print(
                    f"⚠️ VEYL API {response.status} "
                    f"{url} | {text[:200]}"
                )

                return None

            return await response.json()

    except asyncio.TimeoutError:

        print(
            f"⚠️ VEYL API timeout: {url}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"⚠️ VEYL API connection error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"❌ VEYL API error: {error}"
        )

        return None


# ============================================================
# CLEANUP
# ============================================================

async def close_session():

    global _session

    if _session and not _session.closed:

        await _session.close()

    _session = None


# ============================================================
# KLINES
# ============================================================

async def get_klines(symbol):

    return await api_get(
        KLINES_URL,
        {
            "symbol": symbol,
            "interval": INTERVAL,
            "limit": CANDLE_LIMIT,
        },
    )


# ============================================================
# OPEN INTEREST
# ============================================================

async def get_open_interest(symbol):

    return await api_get(
        OPEN_INTEREST_URL,
        {
            "symbol": symbol,
        },
    )


# ============================================================
# FUNDING
# ============================================================

async def get_funding(symbol):

    data = await api_get(
        PREMIUM_URL,
        {
            "symbol": symbol,
        },
    )

    if not isinstance(data, dict):

        return None

    try:

        return {
            "funding_rate": float(
                data.get(
                    "lastFundingRate",
                    0,
                )
            ),
            "mark_price": float(
                data.get(
                    "markPrice",
                    0,
                )
            ),
            "index_price": float(
                data.get(
                    "indexPrice",
                    0,
                )
            ),
            "next_funding_time": int(
                data.get(
                    "nextFundingTime",
                    0,
                )
            ),
        }

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# TAKER BUY / SELL VOLUME
# ============================================================

async def get_taker_volume(symbol):

    data = await api_get(
        TAKER_VOLUME_URL,
        {
            "symbol": symbol,
            "period": "5m",
            "limit": 5,
        },
    )

    if not isinstance(data, list):

        return None

    if not data:

        return None

    try:

        latest = data[-1]

        buy = float(
            latest.get(
                "buyVol",
                0,
            )
        )

        sell = float(
            latest.get(
                "sellVol",
                0,
            )
        )

        total = buy + sell

        if total <= 0:

            return None

        imbalance = (
            buy - sell
        ) / total

        return {
            "buy": buy,
            "sell": sell,
            "total": total,
            "imbalance": imbalance,
        }

    except (
        TypeError,
        ValueError,
        KeyError,
    ):

        return None


# ============================================================
# LIQUIDATIONS
# ============================================================

async def get_liquidations(symbol):

    now = int(
        time.time() * 1000
    )

    start_time = (
        now
        - LIQUIDATION_LOOKBACK_MS
    )

    data = await api_get(
        FORCE_ORDERS_URL,
        {
            "symbol": symbol,
            "limit": 100,
            "startTime": start_time,
            "endTime": now,
        },
    )

    if not isinstance(data, list):

        return {
            "long_usd": 0,
            "short_usd": 0,
            "total_usd": 0,
            "count": 0,
        }

    long_liquidations = 0
    short_liquidations = 0

    count = 0

    for order in data:

        try:

            side = order.get(
                "side",
                ""
            )

            executed_qty = float(
                order.get(
                    "executedQty",
                    0,
                )
            )

            avg_price = float(
                order.get(
                    "avgPrice",
                    0,
                )
            )

            if avg_price <= 0:

                avg_price = float(
                    order.get(
                        "price",
                        0,
                    )
                )

            notional = (
                executed_qty
                * avg_price
            )

            if notional <= 0:

                continue

            count += 1

            # A forced SELL generally closes a LONG.
            if side == "SELL":

                long_liquidations += notional

            # A forced BUY generally closes a SHORT.
            elif side == "BUY":

                short_liquidations += notional

        except (
            TypeError,
            ValueError,
        ):

            continue

    return {

        "long_usd": long_liquidations,

        "short_usd": short_liquidations,

        "total_usd": (
            long_liquidations
            + short_liquidations
        ),

        "count": count,
    }


# ============================================================
# PARSE CANDLES
# ============================================================

def parse_candles(raw):

    candles = []

    if not isinstance(raw, list):

        return candles

    for candle in raw:

        try:

            candles.append({

                "open": float(candle[1]),

                "high": float(candle[2]),

                "low": float(candle[3]),

                "close": float(candle[4]),

                "volume": float(candle[5]),

                "quote_volume": float(
                    candle[7]
                ),

                "close_time": int(
                    candle[6]
                ),
            })

        except (
            TypeError,
            ValueError,
            IndexError,
        ):

            continue

    return candles


# ============================================================
# SAFE DIVISION
# ============================================================

def safe_div(
    numerator,
    denominator,
):

    if denominator is None:

        return 0

    if denominator <= 0:

        return 0

    return numerator / denominator


# ============================================================
# AVERAGE
# ============================================================

def safe_mean(values):

    values = [
        value
        for value in values
        if value is not None
        and value >= 0
    ]

    if not values:

        return 0

    return mean(values)


# ============================================================
# PRICE FORMAT
# ============================================================

def format_price(value):

    if value >= 1000:

        return f"${value:,.2f}"

    if value >= 1:

        return f"${value:,.2f}"

    if value >= 0.01:

        return f"${value:.4f}"

    return f"${value:.8f}"


# ============================================================
# USD FORMAT
# ============================================================

def format_usd(value):

    value = abs(value)

    if value >= 1_000_000_000:

        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:

        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:

        return f"${value / 1_000:.1f}K"

    return f"${value:,.0f}"


# ============================================================
# PERCENT FORMAT
# ============================================================

def format_percent(value):

    return f"{value * 100:+.3f}%"


# ============================================================
# FUNDING FORMAT
# ============================================================

def format_funding(value):

    return f"{value * 100:+.4f}%"


# ============================================================
# RATIO FORMAT
# ============================================================

def format_ratio(value):

    return f"{value:.2f}x"


# ============================================================
# PROGRESS BAR
# ============================================================

def progress_bar(
    value,
    length=12,
):

    value = max(
        0,
        min(
            100,
            value,
        ),
    )

    filled = round(
        value
        / 100
        * length
    )

    return (
        "█" * filled
        + "░" * (
            length
            - filled
        )
    )


# ============================================================
# ANALYZE PRICE STRUCTURE
# ============================================================

def analyze_price(candles):

    if len(candles) < 25:

        return None

    current = candles[-1]

    previous = candles[-2]

    baseline = candles[
        -VOLUME_BASELINE - 1:-1
    ]

    # --------------------------------------------------------
    # CURRENT BODY
    # --------------------------------------------------------

    body = (
        current["close"]
        - current["open"]
    )

    body_abs = abs(body)

    previous_body = abs(
        previous["close"]
        - previous["open"]
    )

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    current_range = (
        current["high"]
        - current["low"]
    )

    historical_ranges = [

        candle["high"]
        - candle["low"]

        for candle in baseline
    ]

    average_range = safe_mean(
        historical_ranges
    )

    volatility_ratio = safe_div(
        current_range,
        average_range,
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    historical_volume = [

        candle["quote_volume"]

        for candle in baseline
    ]

    average_volume = safe_mean(
        historical_volume
    )

    volume_ratio = safe_div(
        current["quote_volume"],
        average_volume,
    )

    # --------------------------------------------------------
    # BODY / RANGE
    # --------------------------------------------------------

    candle_strength = safe_div(
        body_abs,
        current_range,
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum_candles = candles[
        -MOMENTUM_BASELINE:
    ]

    if momentum_candles:

        start_price = (
            momentum_candles[0]["open"]
        )

        momentum = safe_div(
            current["close"]
            - start_price,
            start_price,
        )

    else:

        momentum = 0

    # --------------------------------------------------------
    # PREVIOUS MOMENTUM
    # --------------------------------------------------------

    previous_window = candles[
        -MOMENTUM_BASELINE * 2:
        -MOMENTUM_BASELINE
    ]

    if previous_window:

        previous_start = (
            previous_window[0]["open"]
        )

        previous_end = (
            previous_window[-1]["close"]
        )

        previous_momentum = safe_div(
            previous_end
            - previous_start,
            previous_start,
        )

    else:

        previous_momentum = 0

    momentum_acceleration = safe_div(
        abs(momentum),
        abs(previous_momentum),
    )

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    if body > 0:

        direction = "BULLISH"

    elif body < 0:

        direction = "BEARISH"

    else:

        direction = "NEUTRAL"

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {

        "current_price": current["close"],

        "direction": direction,

        "body": body,

        "body_abs": body_abs,

        "previous_body": previous_body,

        "current_range": current_range,

        "volatility_ratio": volatility_ratio,

        "volume_ratio": volume_ratio,

        "candle_strength": candle_strength,

        "momentum": momentum,

        "momentum_acceleration": (
            momentum_acceleration
        ),

    }


# ============================================================
# OPEN INTEREST ANALYSIS
# ============================================================

def analyze_open_interest(
    current_oi,
    candles,
):

    if not current_oi:

        return {

            "current": 0,

            "change": 0,

            "change_percent": 0,

            "signal": "UNAVAILABLE",

        }

    try:

        current = float(
            current_oi.get(
                "openInterest",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        current = 0

    # We do not have historical OI from this single REST call.
    # Therefore this function gives a current OI reading.
    #
    # The engine also uses price/volume structure to avoid
    # pretending that a single OI snapshot proves an expansion.

    return {

        "current": current,

        "change": 0,

        "change_percent": 0,

        "signal": "CURRENT",

    }


# ============================================================
# CASCADE ANALYSIS
# ============================================================

def analyze_cascade(
    price,
    oi,
    funding,
    taker,
    liquidations,
):

    if not price:

        return None

    # ========================================================
    # SIGNAL FLAGS
    # ========================================================

    volume_signal = (
        price["volume_ratio"]
        >= VOLUME_SPIKE_THRESHOLD
    )

    volatility_signal = (
        price["volatility_ratio"]
        >= VOLATILITY_SPIKE_THRESHOLD
    )

    momentum_signal = (
        price["momentum_acceleration"]
        >= MOMENTUM_SPIKE_THRESHOLD
        and abs(price["momentum"]) >= 0.002
    )

    candle_signal = (
        price["candle_strength"]
        >= 0.60
    )

    # ========================================================
    # TAKER FLOW
    # ========================================================

    taker_imbalance = 0

    taker_signal = False

    if taker:

        taker_imbalance = taker[
            "imbalance"
        ]

        taker_signal = (
            abs(taker_imbalance)
            >= TAKER_IMBALANCE_THRESHOLD
        )

    # ========================================================
    # LIQUIDATION FLOW
    # ========================================================

    long_liqs = liquidations[
        "long_usd"
    ]

    short_liqs = liquidations[
        "short_usd"
    ]

    total_liqs = liquidations[
        "total_usd"
    ]

    liquidation_signal = (
        total_liqs
        >= LIQUIDATION_CONFIRMATION_USD
    )

    # ========================================================
    # LIQUIDATION DIRECTION
    # ========================================================

    if long_liqs > short_liqs:

        liquidation_direction = (
            "LONG LIQUIDATION"
        )

    elif short_liqs > long_liqs:

        liquidation_direction = (
            "SHORT LIQUIDATION"
        )

    else:

        liquidation_direction = (
            "MIXED"
        )

    # ========================================================
    # DIRECTION
    # ========================================================

    direction = price[
        "direction"
    ]

    # ========================================================
    # SCORE
    # ========================================================

    score = 0

    # Price structure — 20
    if momentum_signal:

        score += 10

    if candle_signal:

        score += 10

    # Volume — 20
    if price["volume_ratio"] >= 3:

        score += 20

    elif price["volume_ratio"] >= 2.5:

        score += 17

    elif price["volume_ratio"] >= 1.8:

        score += 12

    # Volatility — 15
    if price["volatility_ratio"] >= 3:

        score += 15

    elif price["volatility_ratio"] >= 2:

        score += 12

    elif price["volatility_ratio"] >= 1.6:

        score += 8

    # Taker flow — 15
    if taker_signal:

        imbalance_strength = abs(
            taker_imbalance
        )

        if imbalance_strength >= 0.30:

            score += 15

        elif imbalance_strength >= 0.20:

            score += 12

        else:

            score += 8

    # Liquidations — 30
    if total_liqs >= 5_000_000:

        score += 30

    elif total_liqs >= 1_000_000:

        score += 25

    elif total_liqs >= 250_000:

        score += 18

    elif total_liqs >= 25_000:

        score += 10

    # ========================================================
    # SCORE CAP
    # ========================================================

    score = min(
        100,
        score,
    )

    # ========================================================
    # CONFIRMATIONS
    # ========================================================

    confirmations = sum([

        volume_signal,

        volatility_signal,

        momentum_signal,

        liquidation_signal,

    ])

    # ========================================================
    # STATUS
    # ========================================================

    if score >= 75 and confirmations >= 3:

        status = "ACTIVE"

    elif score >= 50 and confirmations >= 2:

        status = "WATCH"

    elif score >= 25:

        status = "WEAK"

    else:

        status = "INACTIVE"

    # ========================================================
    # RISK
    # ========================================================

    if score >= 80:

        risk = "EXTREME"

    elif score >= 60:

        risk = "HIGH"

    elif score >= 35:

        risk = "MODERATE"

    else:

        risk = "LOW"

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    if status == "ACTIVE":

        if (
            direction == "BEARISH"
            and long_liqs > short_liqs
        ):

            classification = (
                "LONG LIQUIDATION CASCADE"
            )

        elif (
            direction == "BULLISH"
            and short_liqs > long_liqs
        ):

            classification = (
                "SHORT LIQUIDATION CASCADE"
            )

        elif direction == "BEARISH":

            classification = (
                "BEARISH CASCADE PRESSURE"
            )

        elif direction == "BULLISH":

            classification = (
                "BULLISH CASCADE PRESSURE"
            )

        else:

            classification = "UNCONFIRMED"

    elif direction == "BULLISH":

        classification = (
            "BULLISH PRESSURE"
        )

    elif direction == "BEARISH":

        classification = (
            "BEARISH PRESSURE"
        )

    else:

        classification = "NEUTRAL"

    # ========================================================
    # TAKER SIDE
    # ========================================================

    if taker_imbalance > 0:

        taker_side = "BUY DOMINANT"

    elif taker_imbalance < 0:

        taker_side = "SELL DOMINANT"

    else:

        taker_side = "BALANCED"

    # ========================================================
    # FUNDING STATE
    # ========================================================

    funding_rate = 0

    if funding:

        funding_rate = funding[
            "funding_rate"
        ]

    if funding_rate >= 0.0005:

        funding_state = "LONG BIASED"

    elif funding_rate <= -0.0005:

        funding_state = "SHORT BIASED"

    else:

        funding_state = "NEUTRAL"

    return {

        "score": score,

        "status": status,

        "risk": risk,

        "direction": direction,

        "classification": classification,

        "confirmations": confirmations,

        "volume_signal": volume_signal,

        "volatility_signal": volatility_signal,

        "momentum_signal": momentum_signal,

        "liquidation_signal": liquidation_signal,

        "liquidation_direction": (
            liquidation_direction
        ),

        "long_liquidations": long_liqs,

        "short_liquidations": short_liqs,

        "total_liquidations": total_liqs,

        "taker_imbalance": taker_imbalance,

        "taker_side": taker_side,

        "funding_rate": funding_rate,

        "funding_state": funding_state,

        "open_interest": oi.get(
            "current",
            0,
        ),

        "price": price["current_price"],

        "volume_ratio": price[
            "volume_ratio"
        ],

        "volatility_ratio": price[
            "volatility_ratio"
        ],

        "momentum_acceleration": price[
            "momentum_acceleration"
        ],

        "candle_strength": price[
            "candle_strength"
        ],

    }


# ============================================================
# EMBED
# ============================================================

def create_embed(
    asset,
    symbol,
    analysis,
):

    score = analysis[
        "score"
    ]

    status = analysis[
        "status"
    ]

    # --------------------------------------------------------
    # STATUS LABEL
    # --------------------------------------------------------

    if status == "ACTIVE":

        status_label = (
            "● CASCADE DETECTED"
        )

    elif status == "WATCH":

        status_label = (
            "◐ CASCADE WATCH"
        )

    elif status == "WEAK":

        status_label = (
            "○ MARKET PRESSURE"
        )

    else:

        status_label = (
            "— NO CASCADE"
        )

    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = discord.Embed(

        title="◈ VEYL / CASCADE PRO",

        description=(
            f"**{asset.upper()} / USDT PERPETUAL**\n"
            f"`USDⓈ-M FUTURES`\n\n"
            f"## {format_price(analysis['price'])}\n"
            f"{status_label}"
        ),

        color=VEYL_WHITE,
    )

    # ========================================================
    # MAIN STATUS
    # ========================================================

    embed.add_field(

        name="CASCADE ENGINE",

        value=(
            f"**{analysis['classification']}**\n"
            f"`{status}` • "
            f"Risk: **{analysis['risk']}**\n\n"
            f"Confirmation\n"
            f"`"
            f"{'●' * analysis['confirmations']}"
            f"{'○' * (4 - analysis['confirmations'])}"
            f"` "
            f"**{analysis['confirmations']}/4**"
        ),

        inline=False,
    )

    # ========================================================
    # SCORE
    # ========================================================

    embed.add_field(

        name="CASCADE SCORE",

        value=(
            f"**{score}/100**\n"
            f"`{progress_bar(score)}`"
        ),

        inline=False,
    )

    # ========================================================
    # MARKET STRUCTURE
    # ========================================================

    volume_mark = (
        "✓"
        if analysis["volume_signal"]
        else "—"
    )

    volatility_mark = (
        "✓"
        if analysis["volatility_signal"]
        else "—"
    )

    momentum_mark = (
        "✓"
        if analysis["momentum_signal"]
        else "—"
    )

    embed.add_field(

        name="MARKET STRUCTURE",

        value=(
            f"`{volume_mark}` Volume Expansion\n"
            f"   **{format_ratio(analysis['volume_ratio'])}**\n\n"

            f"`{volatility_mark}` Volatility Expansion\n"
            f"   **{format_ratio(analysis['volatility_ratio'])}**\n\n"

            f"`{momentum_mark}` Momentum Acceleration\n"
            f"   **{format_ratio(analysis['momentum_acceleration'])}**"
        ),

        inline=True,
    )

    # ========================================================
    # LIQUIDATION FLOW
    # ========================================================

    liquidation_mark = (
        "✓"
        if analysis["liquidation_signal"]
        else "—"
    )

    embed.add_field(

        name="LIQUIDATION FLOW",

        value=(
            f"`{liquidation_mark}` "
            f"Forced Orders\n\n"

            f"LONGS\n"
            f"**{format_usd(analysis['long_liquidations'])}**\n\n"

            f"SHORTS\n"
            f"**{format_usd(analysis['short_liquidations'])}**\n\n"

            f"NET EVENT FLOW\n"
            f"**{analysis['liquidation_direction']}**"
        ),

        inline=True,
    )

    # ========================================================
    # ORDER FLOW
    # ========================================================

    imbalance = (
        analysis["taker_imbalance"]
    )

    embed.add_field(

        name="ORDER FLOW",

        value=(
            f"**{analysis['taker_side']}**\n\n"
            f"Taker Imbalance\n"
            f"**{format_percent(imbalance)}**\n\n"
            f"Signal\n"
            f"`"
            f"{'CONFIRMED' if abs(imbalance) >= TAKER_IMBALANCE_THRESHOLD else 'NEUTRAL'}"
            f"`"
        ),

        inline=True,
    )

    # ========================================================
    # DERIVATIVES
    # ========================================================

    oi = analysis[
        "open_interest"
    ]

    embed.add_field(

        name="DERIVATIVES",

        value=(
            f"Open Interest\n"
            f"**{format_usd(oi)}**\n\n"

            f"Funding Rate\n"
            f"**{format_funding(analysis['funding_rate'])}**\n\n"

            f"Position Bias\n"
            f"**{analysis['funding_state']}**"
        ),

        inline=True,
    )

    # ========================================================
    # CANDLE
    # ========================================================

    candle_strength = (
        analysis["candle_strength"]
        * 100
    )

    embed.add_field(

        name="MICROSTRUCTURE",

        value=(
            f"Direction\n"
            f"**{analysis['direction']}**\n\n"

            f"Candle Strength\n"
            f"**{candle_strength:.1f}%**\n\n"

            f"Timeframe\n"
            f"`1 MINUTE`"
        ),

        inline=True,
    )

    # ========================================================
    # ENGINE INFO
    # ========================================================

    embed.add_field(

        name="VEYL INTELLIGENCE",

        value=(
            "`PRICE STRUCTURE`\n"
            "`VOLUME EXPANSION`\n"
            "`VOLATILITY`\n"
            "`TAKER FLOW`\n"
            "`LIQUIDATION FLOW`\n"
            "`FUNDING`\n"
            "`OPEN INTEREST`"
        ),

        inline=False,
    )

    # ========================================================
    # FOOTER
    # ========================================================

    embed.set_footer(

        text=(
            "VEYL CASCADE PRO • "
            "BINANCE USDⓈ-M FUTURES • "
            "MARKET ANALYSIS • NOT FINANCIAL ADVICE"
        )
    )

    return embed


# ============================================================
# ERROR EMBED
# ============================================================

def create_error_embed(
    title,
    description,
):

    embed = discord.Embed(

        title="◈ VEYL / CASCADE PRO",

        description=(
            f"### {title}\n\n"
            f"{description}"
        ),

        color=VEYL_WHITE,
    )

    embed.set_footer(
        text=(
            "VEYL CASCADE PRO • "
            "REQUEST STOPPED SAFELY"
        )
    )

    return embed


# ============================================================
# COG
# ============================================================

class VeylCascade(
    commands.Cog
):

    def __init__(self, bot):

        self.bot = bot

        print(
            "🌊 VEYL Cascade PRO Engine activé."
        )

    # ========================================================
    # COMMAND
    # ========================================================

    @app_commands.command(

        name="cascade",

        description=(
            "VEYL Cascade PRO — "
            "Futures liquidation pressure analysis."
        ),
    )

    @app_commands.describe(

        asset=(
            "Crypto à analyser : BTC, ETH, SOL, BNB..."
        ),
    )

    async def cascade(

        self,
        interaction: discord.Interaction,
        asset: str,

    ):

        await interaction.response.defer()

        asset_clean = (
            asset
            .strip()
            .lower()
        )

        symbol = ASSET_MAP.get(
            asset_clean
        )

        # ====================================================
        # UNKNOWN ASSET
        # ====================================================

        if not symbol:

            embed = create_error_embed(

                "ASSET UNAVAILABLE",

                (
                    f"VEYL could not map "
                    f"**{asset.upper()}** "
                    f"to a supported Futures market."
                ),
            )

            await interaction.followup.send(
                embed=embed
            )

            return

        # ====================================================
        # FETCH DATA IN PARALLEL
        # ====================================================

        results = await asyncio.gather(

            get_klines(symbol),

            get_open_interest(symbol),

            get_funding(symbol),

            get_taker_volume(symbol),

            get_liquidations(symbol),

            return_exceptions=True,
        )

        raw_klines = (
            None
            if isinstance(
                results[0],
                Exception,
            )
            else results[0]
        )

        raw_oi = (
            None
            if isinstance(
                results[1],
                Exception,
            )
            else results[1]
        )

        funding = (
            None
            if isinstance(
                results[2],
                Exception,
            )
            else results[2]
        )

        taker = (
            None
            if isinstance(
                results[3],
                Exception,
            )
            else results[3]
        )

        liquidations = (

            {
                "long_usd": 0,
                "short_usd": 0,
                "total_usd": 0,
                "count": 0,
            }

            if isinstance(
                results[4],
                Exception,
            )

            else results[4]
        )

        # ====================================================
        # KLINE VALIDATION
        # ====================================================

        candles = parse_candles(
            raw_klines
        )

        if len(candles) < 25:

            embed = create_error_embed(

                "MARKET DATA UNAVAILABLE",

                (
                    f"VEYL could not retrieve enough "
                    f"1m Futures data for "
                    f"**{asset.upper()}**.\n\n"
                    "`Analysis stopped safely.`"
                ),
            )

            await interaction.followup.send(
                embed=embed
            )

            return

        # ====================================================
        # PRICE ANALYSIS
        # ====================================================

        price_analysis = analyze_price(
            candles
        )

        if not price_analysis:

            embed = create_error_embed(

                "ANALYSIS FAILED",

                (
                    "VEYL could not calculate "
                    "the market structure."
                ),
            )

            await interaction.followup.send(
                embed=embed
            )

            return

        # ====================================================
        # OI
        # ====================================================

        oi_analysis = analyze_open_interest(

            raw_oi,

            candles,
        )

        # ====================================================
        # CASCADE ENGINE
        # ====================================================

        analysis = analyze_cascade(

            price_analysis,

            oi_analysis,

            funding,

            taker,

            liquidations,
        )

        if not analysis:

            embed = create_error_embed(

                "ENGINE ERROR",

                (
                    "VEYL Cascade PRO could not "
                    "complete the calculation."
                ),
            )

            await interaction.followup.send(
                embed=embed
            )

            return

        # ====================================================
        # EMBED
        # ====================================================

        embed = create_embed(

            asset_clean,

            symbol,

            analysis,
        )

        await interaction.followup.send(
            embed=embed
        )

    # ========================================================
    # UNLOAD
    # ========================================================

    def cog_unload(self):

        asyncio.create_task(
            close_session()
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylCascade(bot)
    )
