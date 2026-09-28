# ============================================================
# VEYL // BINANCE PROVIDER
# Market + Chart Data Provider
# ============================================================

import asyncio
import time
from typing import Optional

import aiohttp


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.binance.com"

PRICE_URL = f"{BASE_URL}/api/v3/ticker/price"
TICKER_URL = f"{BASE_URL}/api/v3/ticker/24hr"
KLINES_URL = f"{BASE_URL}/api/v3/klines"

REQUEST_TIMEOUT = 12

USER_AGENT = "VEYL-Market-Engine/5.0"


# ============================================================
# COIN → BINANCE SYMBOL
# ============================================================

BINANCE_SYMBOLS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "tether": "USDTUSDT",
    "binancecoin": "BNBUSDT",
    "solana": "SOLUSDT",
    "usd-coin": "USDCUSDT",
    "ripple": "XRPUSDT",
    "dogecoin": "DOGEUSDT",
    "cardano": "ADAUSDT",
    "avalanche-2": "AVAXUSDT",
    "chainlink": "LINKUSDT",
    "shiba-inu": "SHIBUSDT",
    "tron": "TRXUSDT",
    "polkadot": "DOTUSDT",
    "litecoin": "LTCUSDT",
    "uniswap": "UNIUSDT",
    "sui": "SUIUSDT",
    "arbitrum": "ARBUSDT",
    "optimism": "OPUSDT",
    "pepe": "PEPEUSDT",
    "bitcoin-cash": "BCHUSDT",
    "stellar": "XLMUSDT",
    "near": "NEARUSDT",
    "cosmos": "ATOMUSDT",
    "aptos": "APTUSDT",
    "internet-computer": "ICPUSDT",
    "hedera-hashgraph": "HBARUSDT",
}


# ============================================================
# CACHE
# ============================================================

_price_cache = {}
_chart_cache = {}
_ohlcv_cache = {}

PRICE_CACHE_TTL = 5
CHART_CACHE_TTL = 45
OHLCV_CACHE_TTL = 30


# ============================================================
# SESSION
# ============================================================

_session: Optional[aiohttp.ClientSession] = None


async def _get_session():

    global _session

    if _session is None or _session.closed:

        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT
        )

        _session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )

    return _session


async def close():

    global _session

    if _session and not _session.closed:
        await _session.close()

    _session = None


# ============================================================
# REQUEST
# ============================================================

async def _request(
    url,
    params=None,
):

    session = await _get_session()

    try:

        async with session.get(
            url,
            params=params,
        ) as response:

            if response.status in (418, 429):
                retry_after = response.headers.get("Retry-After", "?")
                print(f"VEYL Binance: HTTP {response.status}; Retry-After={retry_after}.")
                return None

            if response.status != 200:
                print(f"VEYL Binance: HTTP {response.status}.")
                return None

            return await response.json()

    except asyncio.TimeoutError:

        print(
            "VEYL Binance: request timeout."
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"VEYL Binance connection error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"VEYL Binance error: {error}"
        )

        return None


# ============================================================
# SYMBOL RESOLUTION
# ============================================================

def get_symbol(coin_id):

    if not coin_id:
        return None

    return BINANCE_SYMBOLS.get(
        str(coin_id).lower()
    )


# ============================================================
# PRICE
# ============================================================

async def get_price(
    coin_id,
):

    symbol = get_symbol(
        coin_id
    )

    if not symbol:
        return None

    now = time.monotonic()

    cached = _price_cache.get(
        coin_id
    )

    if cached:

        value, created = cached

        if now - created < PRICE_CACHE_TTL:
            return value

    data = await _request(
        PRICE_URL,
        {
            "symbol": symbol,
        },
    )

    if not data:
        if cached and now - cached[1] < 120:
            return cached[0]
        return None

    try:

        price = float(
            data["price"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return None

    result = {
        "id": coin_id,
        "price": price,
        "usd": price,
        "provider": "binance",
        "symbol": symbol,
    }

    _price_cache[coin_id] = (
        result,
        now,
    )

    return result


# ============================================================
# 24H TICKER
# ============================================================

async def get_ticker(
    coin_id,
):

    symbol = get_symbol(
        coin_id
    )

    if not symbol:
        return None

    data = await _request(
        TICKER_URL,
        {
            "symbol": symbol,
        },
    )

    if not data:
        return None

    try:

        price = float(
            data["lastPrice"]
        )

        change = float(
            data["priceChangePercent"]
        )

        volume = float(
            data["quoteVolume"]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):

        return None

    return {
        "id": coin_id,
        "price": price,
        "usd": price,
        "24h_change": change,
        "24h_volume": volume,
        "provider": "binance",
        "symbol": symbol,
    }


# ============================================================
# OHLCV — PREDICTION ENGINE
# ============================================================

async def get_ohlcv(
    coin_id: str,
    interval: str = "15m",
    limit: int = 200,
):
    """Return real Binance OHLCV candles for VEYL Quant."""
    symbol = get_symbol(coin_id)
    if not symbol:
        return None

    allowed_intervals = {
        "1m", "3m", "5m", "15m", "30m", "1h",
        "2h", "4h", "6h", "8h", "12h", "1d",
    }
    if interval not in allowed_intervals:
        interval = "15m"

    limit = max(20, min(int(limit), 1000))
    cache_key = (coin_id, interval, limit)
    now = time.monotonic()
    cached = _ohlcv_cache.get(cache_key)

    if cached and now - cached[1] < OHLCV_CACHE_TTL:
        return cached[0]

    data = await _request(
        KLINES_URL,
        {"symbol": symbol, "interval": interval, "limit": limit},
    )

    if not isinstance(data, list):
        return cached[0] if cached else None

    candles = []
    for row in data:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            candles.append({
                "timestamp": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        except (TypeError, ValueError):
            continue

    if len(candles) < 20:
        return cached[0] if cached else None

    _ohlcv_cache[cache_key] = (candles, now)
    return candles


# ============================================================
# CHART
# ============================================================

async def get_chart(
    coin_id,
    days=1,
):

    symbol = get_symbol(
        coin_id
    )

    if not symbol:
        return None

    days = int(days)

    # --------------------------------------------------------
    # Binance intervals
    # --------------------------------------------------------

    if days <= 1:

        interval = "5m"
        limit = 288

    elif days <= 3:

        interval = "15m"
        limit = 288

    elif days <= 7:

        interval = "1h"
        limit = 168

    elif days <= 30:

        interval = "4h"
        limit = 180

    else:

        interval = "1d"
        limit = min(days, 1000)

    cache_key = (
        coin_id,
        days,
        interval,
    )

    now = time.monotonic()

    cached = _chart_cache.get(
        cache_key
    )

    if cached:

        data, created = cached

        if now - created < CHART_CACHE_TTL:
            return data

    data = await _request(
        KLINES_URL,
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    if not data:
        return None

    prices = []

    for candle in data:

        if not isinstance(
            candle,
            list,
        ):
            continue

        if len(candle) < 2:
            continue

        try:

            timestamp = float(
                candle[0]
            )

            close_price = float(
                candle[4]
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        prices.append(
            [
                timestamp,
                close_price,
            ]
        )

    if len(prices) < 2:
        return None

    result = {
        "prices": prices,
        "provider": "binance",
        "symbol": symbol,
        "interval": interval,
        "days": days,
    }

    _chart_cache[cache_key] = (
        result,
        now,
    )

    return result