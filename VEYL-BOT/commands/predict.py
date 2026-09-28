from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from services.assets import PREDICT_ASSETS, get_asset
from services.market import get_crypto_price_async
from services.providers import binance, coingecko
from services.quant import (
    analyze_trend,
    analyze_momentum,
    analyze_structure,
    analyze_smart_money,
    analyze_volume,
    analyze_volatility,
    analyze_statistics,
    calculate_confluence,
)


# ============================================================
# PREDICT ASSET MENU
# Discord allows a maximum of 25 choices per option.
# These are the 25 assets defined in services/assets.py.
# ============================================================

PREDICT_CHOICES = [
    app_commands.Choice(
        name=f"{asset.name} ({asset.symbol})",
        value=asset.coin_id,
    )
    for asset in PREDICT_ASSETS[:25]
]


PREDICT_INTERVAL = "15m"
PREDICT_LIMIT = 200


# ============================================================
# PREDICT VIEW
# ============================================================

class PredictView(discord.ui.View):

    def __init__(self, coin_id: str):
        super().__init__(timeout=300)
        self.coin_id = coin_id

    @discord.ui.button(
        label="Refresh",
        style=discord.ButtonStyle.secondary,
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.defer()

        try:
            candles, provider = await fetch_prediction_data(
                self.coin_id
            )

            if not candles:
                await interaction.followup.send(
                    "❌ Impossible de récupérer les données OHLCV pour cette crypto.",
                    ephemeral=True,
                )
                return

            result = await run_prediction(
                self.coin_id,
                candles,
                provider,
            )

            await interaction.message.edit(
                embed=build_predict_embed(result),
                view=PredictView(self.coin_id),
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ Le fournisseur de données a mis trop de temps à répondre.",
                ephemeral=True,
            )

        except aiohttp.ClientError:
            await interaction.followup.send(
                "❌ Le fournisseur de données marché est indisponible.",
                ephemeral=True,
            )

        except Exception as exc:
            print(
                f"[PREDICT REFRESH ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            await interaction.followup.send(
                "❌ VEYL prediction engine encountered an error.",
                ephemeral=True,
            )


# ============================================================
# COINGECKO FALLBACK
# ============================================================

async def _coingecko_candles(
    coin_id: str,
) -> list[dict]:

    """
    Build OHLC candles from CoinGecko close-price history
    as a fallback when Binance is unavailable.
    """

    data = await coingecko.get_chart(
        coin_id,
        days=2,
    )

    if not data:
        return []

    prices = data.get("prices") or []

    candles: list[dict] = []

    previous_close: float | None = None

    for point in prices:

        if not isinstance(
            point,
            (list, tuple),
        ):
            continue

        if len(point) < 2:
            continue

        try:
            timestamp = int(
                float(point[0])
            )

            close = float(
                point[1]
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if close <= 0:
            continue

        open_price = (
            previous_close
            if previous_close
            and previous_close > 0
            else close
        )

        high = max(
            open_price,
            close,
        )

        low = min(
            open_price,
            close,
        )

        candles.append(
            {
                "timestamp": timestamp,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 0.0,
            }
        )

        previous_close = close

    # Quant engine needs enough history.
    if len(candles) < 20:
        return []

    return candles[-PREDICT_LIMIT:]


# ============================================================
# MARKET DATA
# ============================================================

async def fetch_prediction_data(
    coin_id: str,
) -> tuple[list[dict], str]:

    """
    Binance first.
    CoinGecko fallback if Binance has no data.
    """

    candles = await binance.get_ohlcv(
        coin_id,
        interval=PREDICT_INTERVAL,
        limit=PREDICT_LIMIT,
    )

    if candles:
        return candles, "BINANCE"

    candles = await _coingecko_candles(
        coin_id
    )

    if candles:
        return candles, "COINGECKO"

    return [], "UNAVAILABLE"


# ============================================================
# PREDICTION ENGINE
# ============================================================

async def run_prediction(
    coin_id: str,
    candles: list[dict],
    provider: str,
) -> dict:

    (
        trend,
        momentum,
        structure,
        smart_money,
        volume,
        volatility,
        statistics,
    ) = await asyncio.gather(

        asyncio.to_thread(
            analyze_trend,
            candles,
        ),

        asyncio.to_thread(
            analyze_momentum,
            candles,
        ),

        asyncio.to_thread(
            analyze_structure,
            candles,
        ),

        asyncio.to_thread(
            analyze_smart_money,
            candles,
        ),

        asyncio.to_thread(
            analyze_volume,
            candles,
        ),

        asyncio.to_thread(
            analyze_volatility,
            candles,
        ),

        asyncio.to_thread(
            analyze_statistics,
            candles,
        ),
    )

    # Whale/on-chain engine is not connected yet.
    # Neutral value prevents artificial bullish/bearish bias.
    whales = 50.0

    confluence = calculate_confluence(
        trend=trend,
        momentum=momentum,
        structure=structure,
        smart_money=smart_money,
        volume=volume,
        volatility=volatility,
        statistics=statistics,
        whales=whales,
    )

    asset = get_asset(
        coin_id
    )

    market = (
        await get_crypto_price_async(
            coin_id
        )
        or {}
    )

    last_close = float(
        candles[-1]["close"]
    )

    fallback_change = 0.0

    if len(candles) >= 2:

        reference = candles[
            max(
                0,
                len(candles) - 97,
            )
        ]

        reference_close = float(
            reference["close"]
        )

        if reference_close > 0:

            fallback_change = (
                (
                    last_close
                    - reference_close
                )
                / reference_close
            ) * 100

    token = {

        "name": (
            asset.name
            if asset
            else market.get(
                "name",
                "Unknown",
            )
        ),

        "symbol": (
            asset.symbol
            if asset
            else market.get(
                "symbol",
                coin_id.upper(),
            )
        ),

        "price": float(
            market.get("price")
            or last_close
        ),

        "volume_24h": float(
            market.get("24h_volume")
            or 0
        ),

        "price_change_24h": float(
            market.get(
                "24h_change"
            )
            if market.get(
                "24h_change"
            ) is not None
            else fallback_change
        ),

        "provider": market.get(
            "provider",
            provider.lower(),
        ),
    }

    return {

        "coin_id": coin_id,

        "token": token,

        "provider": provider,

        "interval": PREDICT_INTERVAL,

        "candles": len(candles),

        "trend": trend,

        "momentum": momentum,

        "structure": structure,

        "smart_money": smart_money,

        "volume": volume,

        "volatility": volatility,

        "statistics": statistics,

        "whales": whales,

        "confluence": confluence,
    }


# ============================================================
# SCORE BAR
# ============================================================

def score_bar(
    score: float,
) -> str:

    filled = max(
        0,
        min(
            10,
            int(
                round(
                    score / 10
                )
            ),
        ),
    )

    return (
        "█" * filled
        + "░" * (10 - filled)
    )


# ============================================================
# SAFE FLOAT
# ============================================================

def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# PREDICT EMBED
# ============================================================

def build_predict_embed(
    result: dict,
) -> discord.Embed:

    token = result["token"]

    confluence = result[
        "confluence"
    ]

    name = token.get(
        "name",
        "Unknown",
    )

    symbol = token.get(
        "symbol",
        "???",
    )

    score = _safe_float(
        confluence.get(
            "score"
        ),
        50,
    )

    bias = confluence.get(
        "bias",
        "NEUTRAL",
    )

    strength = confluence.get(
        "strength",
        "LOW",
    )

    title = (
        f"⌘ VEYL / PREDICT — {bias}"
    )

    embed = discord.Embed(

        title=title,

        description=(
            f"**{name}** (`{symbol}`)\n"
            f"`{result['interval']}` • "
            f"`{result['candles']} candles` • "
            f"`{result['provider']}`"
        ),

        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(

        name="◈ VEYL CONFLUENCE",

        value=(
            f"**{score:.1f}/100**\n"
            f"`{score_bar(score)}`\n\n"
            f"**BIAS:** `{bias}`\n"
            f"**STRENGTH:** `{strength}`"
        ),

        inline=False,
    )

    fields = [

        (
            "TREND",
            result["trend"],
        ),

        (
            "MOMENTUM",
            result["momentum"],
        ),

        (
            "STRUCTURE",
            result["structure"],
        ),

        (
            "SMART MONEY",
            result["smart_money"],
        ),
    ]

    for label, data in fields:

        embed.add_field(

            name=label,

            value=(
                f"**"
                f"{_safe_float(data.get('score'), 50):.0f}"
                f"/100**\n"
                f"`{data.get('bias', 'NEUTRAL')}`"
            ),

            inline=True,
        )

    embed.add_field(

        name="VOLUME",

        value=(
            f"**"
            f"{_safe_float(result['volume'].get('score'), 50):.0f}"
            f"/100**\n"
            f"`{result['volume'].get('bias', 'NEUTRAL')}`\n"
            f"RVOL: "
            f"`{_safe_float(result['volume'].get('rvol'), 1):.2f}x`"
        ),

        inline=True,
    )

    embed.add_field(

        name="VOLATILITY",

        value=(
            f"**"
            f"{_safe_float(result['volatility'].get('score'), 50):.0f}"
            f"/100**\n"
            f"`{result['volatility'].get('regime', 'NORMAL')}`"
        ),

        inline=True,
    )

    embed.add_field(

        name="STATISTICS",

        value=(
            f"**"
            f"{_safe_float(result['statistics'].get('score'), 50):.0f}"
            f"/100**\n"
            f"Z-Score: "
            f"`{_safe_float(result['statistics'].get('z_score'), 0):.2f}`"
        ),

        inline=True,
    )

    embed.add_field(

        name="WHALE FLOW",

        value=(
            "**50/100**\n"
            "`NEUTRAL — engine not connected`"
        ),

        inline=True,
    )

    all_signals: list[str] = []

    for key in (
        "trend",
        "momentum",
        "structure",
        "smart_money",
        "volume",
        "volatility",
        "statistics",
    ):

        all_signals.extend(
            result[key].get(
                "signals",
                [],
            )
        )

    unique_signals = list(
        dict.fromkeys(
            all_signals
        )
    )

    signals_text = (

        "\n".join(
            f"• {signal}"
            for signal
            in unique_signals[:8]
        )

        if unique_signals

        else
        "• No dominant signal detected."
    )

    embed.add_field(

        name="◈ KEY SIGNALS",

        value=signals_text,

        inline=False,
    )

    price = _safe_float(
        token.get("price")
    )

    volume_24h = _safe_float(
        token.get("volume_24h")
    )

    change = _safe_float(
        token.get(
            "price_change_24h"
        )
    )

    embed.add_field(

        name="MARKET DATA",

        value=(
            f"Price: `${price:,.8f}`\n"
            f"Volume 24h: `${volume_24h:,.0f}`\n"
            f"Change 24h: `{change:+.2f}%`\n"
            f"Market provider: "
            f"`{token.get('provider', result['provider'])}`"
        ),

        inline=False,
    )

    embed.set_footer(
        text=(
            "VEYL Quant Engine • "
            "Analytical signal, not financial advice"
        )
    )

    return embed


# ============================================================
# PREDICT COMMAND
# ============================================================

class Predict(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="predict",
        description=(
            "Analyze a crypto using the VEYL Quant Engine."
        ),
    )
    @app_commands.describe(
        crypto=(
            "Select a cryptocurrency"
        ),
    )
    @app_commands.choices(
        crypto=PREDICT_CHOICES
    )
    async def predict(

        self,

        interaction: discord.Interaction,

        crypto: app_commands.Choice[str],
    ):
        """
        /predict

        The user selects one of the 25 VEYL cryptocurrencies.
        No mint address is accepted or requested.
        """

        await interaction.response.defer()

        # ====================================================
        # GET SELECTED ASSET
        # ====================================================

        coin_id = crypto.value

        asset = get_asset(
            coin_id
        )

        if asset is None:

            await interaction.followup.send(

                "❌ Crypto invalide. "
                "Sélectionne une crypto dans le menu VEYL.",

                ephemeral=True,
            )

            return

        try:

            # =================================================
            # FETCH MARKET DATA
            # =================================================

            candles, provider = (
                await fetch_prediction_data(
                    asset.coin_id
                )
            )

            if not candles:

                await interaction.followup.send(

                    "❌ Aucune donnée OHLCV disponible "
                    f"pour **{asset.name} ({asset.symbol})**.",

                    ephemeral=True,
                )

                return

            # =================================================
            # RUN VEYL QUANT ENGINE
            # =================================================

            result = await run_prediction(

                asset.coin_id,

                candles,

                provider,
            )

            # =================================================
            # SEND RESULT
            # =================================================

            await interaction.followup.send(

                embed=build_predict_embed(
                    result
                ),

                view=PredictView(
                    asset.coin_id
                ),
            )

        except asyncio.TimeoutError:

            await interaction.followup.send(

                "❌ Le fournisseur de données "
                "a mis trop de temps à répondre.",

                ephemeral=True,
            )

        except aiohttp.ClientError:

            await interaction.followup.send(

                "❌ Le fournisseur de données "
                "marché est indisponible.",

                ephemeral=True,
            )

        except Exception as exc:

            print(
                f"[PREDICT ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            await interaction.followup.send(

                "❌ VEYL prediction engine "
                "encountered an error.",

                ephemeral=True,
            )


# ============================================================
# EXTENSION SETUP
# ============================================================

async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Predict(bot)
    )