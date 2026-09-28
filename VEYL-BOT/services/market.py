# ============================================================
# VEYL // MARKET ENGINE
# Central Provider Router
# Binance → Primary
# CoinGecko → Fallback
# ============================================================

import time
from typing import Optional

from services.providers import binance
from services.providers import coingecko
from services.assets import PREDICT_ASSETS


# ============================================================
# CONFIG
# ============================================================

PRICE_CACHE_TTL = 5

# ============================================================
# COINS
# ============================================================

COINS = [
    (asset.coin_id, asset.symbol, asset.name)
    for asset in PREDICT_ASSETS
] + [
    ("tether", "USDT", "Tether"),
    ("usd-coin", "USDC", "USD Coin"),
]



# ============================================================
# ALIASES
# ============================================================

COIN_IDS = {
    asset.coin_id: asset.coin_id
    for asset in PREDICT_ASSETS
}

for asset in PREDICT_ASSETS:
    COIN_IDS[asset.symbol.lower()] = asset.coin_id
    COIN_IDS[asset.name.lower()] = asset.coin_id

COIN_IDS.update({
    "usdt": "tether",
    "tether": "tether",
    "usdc": "usd-coin",
    "usd coin": "usd-coin",
    "usdcoin": "usd-coin",
})



# ============================================================
# CACHE
# ============================================================

_price_cache = {}


# ============================================================
# NORMALIZE
# ============================================================

def normalize_coin(
    identifier: str,
) -> Optional[str]:

    if not identifier:
        return None

    value = str(
        identifier
    ).strip().lower()

    return COIN_IDS.get(
        value,
        value,
    )


# ============================================================
# FIND COIN
# ============================================================

def find_coin(
    identifier: str,
):

    if not identifier:
        return None

    value = str(
        identifier
    ).strip().lower()

    for coin_id, symbol, name in COINS:

        if value in (
            coin_id.lower(),
            symbol.lower(),
            name.lower(),
        ):

            return (
                coin_id,
                symbol,
                name,
            )

    return None


# ============================================================
# PRICE
# ============================================================

async def get_crypto_price_async(
    crypto,
    currency="usd",
):

    coin_id = normalize_coin(
        crypto
    )

    if not coin_id:
        return None

    now = time.monotonic()

    cached = _price_cache.get(
        coin_id
    )

    if cached:

        data, created = cached

        if now - created < PRICE_CACHE_TTL:

            return data

    # ========================================================
    # PROVIDER 1 — BINANCE
    # ========================================================

    result = await binance.get_ticker(
        coin_id
    )

    if result:

        print(
            f"⌘ VEYL Market → Binance {coin_id}"
        )

        _price_cache[coin_id] = (
            result,
            now,
        )

        return result

    # ========================================================
    # PROVIDER 2 — COINGECKO
    # ========================================================

    result = await coingecko.get_price(
        coin_id
    )

    if result:

        print(
            f"⌘ VEYL Market fallback → CoinGecko {coin_id}"
        )

        _price_cache[coin_id] = (
            result,
            now,
        )

        return result

    print(
        f"⚠️ VEYL Market: no provider available for {coin_id}"
    )

    return None


# ============================================================
# GET COIN DATA
# ============================================================

async def get_coin_data(
    crypto,
):

    return await get_crypto_price_async(
        crypto
    )


# ============================================================
# MARKET DATA
# ============================================================

async def get_market_data():

    results = []

    for coin_id, symbol, name in COINS:

        data = await get_crypto_price_async(
            coin_id
        )

        if data:

            results.append(
                {
                    "id": coin_id,
                    "symbol": symbol,
                    "name": name,
                    **data,
                }
            )

    return results


# ============================================================
# MARKETS
# ============================================================

async def get_markets():

    return await get_market_data()


# ============================================================
# CACHE
# ============================================================

def clear_cache():

    _price_cache.clear()

    print(
        "⌘ VEYL Market cache cleared."
    )


# ============================================================
# STATUS
# ============================================================

def get_cache_status():

    return {
        "price_cache_entries": len(
            _price_cache
        )
    }


def market_engine_status():

    return {
        "engine": "VEYL MARKET ENGINE",
        "status": "ONLINE",
        "primary": "BINANCE",
        "fallback": "COINGECKO",
        "assets": len(COINS),
        "cache_ttl": PRICE_CACHE_TTL,
    }