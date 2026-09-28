# ============================================================
# VEYL // COINGECKO PROVIDER
# Fallback Market + Chart Provider
# ============================================================

import asyncio
import time
from typing import Optional

import aiohttp


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://api.coingecko.com/api/v3"

PRICE_URL = f"{BASE_URL}/simple/price"

CHART_URL = (
    f"{BASE_URL}/coins/{{}}/market_chart"
)

REQUEST_TIMEOUT = 15

USER_AGENT = "VEYL-CoinGecko-Provider/5.1"

_cooldown_until = 0.0
_cooldown_seconds = 60.0


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
    global _cooldown_until, _cooldown_seconds

    if time.monotonic() < _cooldown_until:
        return None

    session = await _get_session()

    try:

        async with session.get(
            url,
            params=params,
        ) as response:

            if response.status == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    _cooldown_seconds = max(30.0, min(float(retry_after), 900.0)) if retry_after else 60.0
                except (TypeError, ValueError):
                    _cooldown_seconds = 60.0
                _cooldown_until = time.monotonic() + _cooldown_seconds
                print(f"VEYL CoinGecko: HTTP 429. Cooldown {_cooldown_seconds:.0f}s.")
                return None

            if response.status != 200:

                print(
                    f"VEYL CoinGecko: HTTP "
                    f"{response.status}."
                )

                return None

            return await response.json()

    except asyncio.TimeoutError:

        print(
            "VEYL CoinGecko: request timeout."
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"VEYL CoinGecko connection error: {error}"
        )

        return None

    except Exception as error:

        print(
            f"VEYL CoinGecko error: {error}"
        )

        return None


# ============================================================
# PRICE
# ============================================================

async def get_price(
    coin_id,
):

    data = await _request(
        PRICE_URL,
        {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        },
    )

    if not data:
        return None

    coin = data.get(
        coin_id
    )

    if not coin:
        return None

    return {
        "id": coin_id,

        "price": coin.get(
            "usd"
        ),

        "usd": coin.get(
            "usd"
        ),

        "24h_change": coin.get(
            "usd_24h_change"
        ),

        "market_cap": coin.get(
            "usd_market_cap"
        ),

        "24h_volume": coin.get(
            "usd_24h_vol"
        ),

        "provider": "coingecko",
    }


# ============================================================
# CHART
# ============================================================

async def get_chart(
    coin_id,
    days=1,
):

    data = await _request(
        CHART_URL.format(
            coin_id
        ),
        {
            "vs_currency": "usd",
            "days": str(days),
        },
    )

    if not data:
        return None

    if not isinstance(
        data,
        dict,
    ):
        return None

    prices = data.get(
        "prices"
    )

    if not prices:
        return None

    return {
        "prices": prices,
        "provider": "coingecko",
        "days": days,
    }