# ============================================================
# VEYL / CORRELATION ENGINE
# Institutional Crypto Correlation Monitor
#
# Data source:
#   Binance public API
#
# No CoinGecko dependency.
# ============================================================

import asyncio
import aiohttp
import discord

from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

BINANCE_URL = "https://api.binance.com/api/v3/klines"

INTERVAL = "1h"
CANDLES = 168          # 7 days × 24h
TIMEOUT = 12

ASSETS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
}


# ============================================================
# HTTP SESSION
# ============================================================

async def fetch_klines(symbol: str):

    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": CANDLES,
    }

    timeout = aiohttp.ClientTimeout(
        total=TIMEOUT
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                BINANCE_URL,
                params=params,
            ) as response:

                if response.status != 200:

                    print(
                        f"⚠️ Correlation Binance HTTP "
                        f"{response.status} • {symbol}"
                    )

                    return []

                data = await response.json()

                if not isinstance(data, list):
                    return []

                closes = []

                for candle in data:

                    try:
                        closes.append(
                            float(candle[4])
                        )

                    except (
                        TypeError,
                        ValueError,
                        IndexError,
                    ):
                        continue

                return closes

    except asyncio.CancelledError:
        raise

    except Exception as error:

        print(
            f"⚠️ Correlation fetch error "
            f"{symbol}: {error}"
        )

        return []


# ============================================================
# RETURNS
# ============================================================

def calculate_returns(prices):

    if len(prices) < 2:
        return []

    returns = []

    for index in range(
        1,
        len(prices),
    ):

        previous = prices[index - 1]
        current = prices[index]

        if previous == 0:
            continue

        returns.append(
            (current - previous)
            / previous
        )

    return returns


# ============================================================
# CORRELATION
# ============================================================

def correlation(
    first,
    second,
):

    length = min(
        len(first),
        len(second),
    )

    if length < 3:
        return None

    first = first[:length]
    second = second[:length]

    mean_first = sum(first) / length
    mean_second = sum(second) / length

    numerator = 0.0
    first_variance = 0.0
    second_variance = 0.0

    for x, y in zip(
        first,
        second,
    ):

        dx = x - mean_first
        dy = y - mean_second

        numerator += dx * dy
        first_variance += dx * dx
        second_variance += dy * dy

    denominator = (
        first_variance
        * second_variance
    ) ** 0.5

    if denominator == 0:
        return None

    return numerator / denominator


# ============================================================
# FORMAT
# ============================================================

def correlation_label(value):

    if value is None:
        return "NO DATA"

    if value >= 0.80:
        return "VERY HIGH"

    if value >= 0.60:
        return "HIGH"

    if value >= 0.40:
        return "MODERATE"

    if value >= 0.20:
        return "LOW"

    if value > -0.20:
        return "NEUTRAL"

    if value > -0.40:
        return "NEGATIVE"

    if value > -0.60:
        return "HIGH NEGATIVE"

    return "STRONG NEGATIVE"


def correlation_bar(value):

    if value is None:
        return "░░░░░░░░░░"

    normalized = (
        value + 1
    ) / 2

    normalized = max(
        0,
        min(
            1,
            normalized,
        ),
    )

    length = 10

    filled = round(
        normalized * length
    )

    return (
        "█" * filled
        + "░" * (
            length - filled
        )
    )


def format_correlation(value):

    if value is None:
        return "—"

    return f"{value:+.2f}"


# ============================================================
# ENGINE
# ============================================================

async def build_correlation_data():

    historical = {}

    for asset, symbol in ASSETS.items():

        prices = await fetch_klines(
            symbol
        )

        if len(prices) >= 3:

            historical[asset] = (
                calculate_returns(prices)
            )

    return historical


# ============================================================
# EMBED
# ============================================================

def build_embed(
    base,
    historical,
):

    pairs = []

    base_data = historical.get(
        base
    )

    if not base_data:

        return discord.Embed(
            title="⌘ VEYL / CORRELATION",
            description=(
                "```text\n"
                "CORRELATION ENGINE\n"
                "──────────────────────────────\n"
                "STATUS       DATA ERROR\n"
                "BASE         "
                f"{base}\n"
                "──────────────────────────────\n"
                "```"
            ),
            color=0x18191C,
        )

    for asset, values in historical.items():

        if asset == base:
            continue

        value = correlation(
            base_data,
            values,
        )

        if value is None:
            continue

        pairs.append(
            (
                value,
                asset,
            )
        )

    pairs.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    embed = discord.Embed(
        title=(
            f"⌘ VEYL / CORRELATION / {base}"
        ),
        description=(
            "```text\n"
            "VEYL CORRELATION ENGINE\n"
            "────────────────────────────────────\n"
            f"BASE ASSET   {base}\n"
            "TIMEFRAME    7 DAYS\n"
            "INTERVAL     1H\n"
            "SOURCE       BINANCE\n"
            "ASSETS       8\n"
            "STATUS       ONLINE\n"
            "────────────────────────────────────\n"
            "```"
        ),
        color=0x18191C,
    )

    # --------------------------------------------------------
    # STRONGEST POSITIVE
    # --------------------------------------------------------

    strongest_positive = sorted(
        pairs,
        key=lambda item: item[0],
        reverse=True,
    )[:3]

    positive_text = ""

    for value, asset in strongest_positive:

        positive_text += (
            f"`{asset:<4}` "
            f"`{format_correlation(value):>6}` "
            f"`{correlation_label(value)}`\n"
        )

    embed.add_field(
        name="▲ STRONGEST POSITIVE",
        value=(
            positive_text
            or "No data."
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # STRONGEST NEGATIVE
    # --------------------------------------------------------

    strongest_negative = sorted(
        pairs,
        key=lambda item: item[0],
    )[:3]

    negative_text = ""

    for value, asset in strongest_negative:

        negative_text += (
            f"`{asset:<4}` "
            f"`{format_correlation(value):>6}` "
            f"`{correlation_label(value)}`\n"
        )

    embed.add_field(
        name="▼ STRONGEST NEGATIVE",
        value=(
            negative_text
            or "No data."
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # MATRIX
    # --------------------------------------------------------

    matrix = (
        "```text\n"
        "ASSET       CORRELATION       SIGNAL\n"
        "────────────────────────────────────\n"
    )

    for value, asset in pairs:

        matrix += (
            f"{asset:<11}"
            f"{format_correlation(value):<19}"
            f"{correlation_label(value)}\n"
        )

    matrix += (
        "────────────────────────────────────\n"
        "```"
    )

    embed.add_field(
        name="▤ CORRELATION MATRIX",
        value=matrix,
        inline=False,
    )

    # --------------------------------------------------------
    # INTERPRETATION
    # --------------------------------------------------------

    if pairs:

        highest = pairs[0]
        lowest = pairs[-1]

        interpretation = (
            f"**Highest correlation:** "
            f"`{highest[1]}` "
            f"`{highest[0]:+.2f}`\n"
            f"**Lowest correlation:** "
            f"`{lowest[1]}` "
            f"`{lowest[0]:+.2f}`"
        )

    else:

        interpretation = (
            "Insufficient market data."
        )

    embed.add_field(
        name="⌘ VEYL READ",
        value=interpretation,
        inline=False,
    )

    embed.set_footer(
        text=(
            "VEYL • CORRELATION ENGINE • "
            "BINANCE • 7D • 1H"
        )
    )

    return embed


# ============================================================
# COG
# ============================================================

class Correlation(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):

        self.bot = bot

        print(
            "⌘ VEYL Correlation Engine activated."
        )

    # ========================================================
    # /CORRELATION
    # ========================================================

    @app_commands.command(
        name="correlation",
        description=(
            "Analyse la corrélation entre les crypto-actifs."
        ),
    )
    @app_commands.describe(
        asset=(
            "Crypto de référence "
            "(BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX)"
        )
    )
    @app_commands.choices(
        asset=[
            app_commands.Choice(
                name="Bitcoin (BTC)",
                value="BTC",
            ),
            app_commands.Choice(
                name="Ethereum (ETH)",
                value="ETH",
            ),
            app_commands.Choice(
                name="Solana (SOL)",
                value="SOL",
            ),
            app_commands.Choice(
                name="BNB",
                value="BNB",
            ),
            app_commands.Choice(
                name="XRP",
                value="XRP",
            ),
            app_commands.Choice(
                name="Cardano (ADA)",
                value="ADA",
            ),
            app_commands.Choice(
                name="Dogecoin (DOGE)",
                value="DOGE",
            ),
            app_commands.Choice(
                name="Avalanche (AVAX)",
                value="AVAX",
            ),
        ]
    )
    async def correlation_command(
        self,
        interaction: discord.Interaction,
        asset: app_commands.Choice[str],
    ):

        await interaction.response.defer()

        base = asset.value.upper()

        try:

            historical = (
                await build_correlation_data()
            )

            if not historical:

                await interaction.followup.send(
                    (
                        "⚠️ VEYL Correlation : "
                        "aucune donnée disponible."
                    ),
                    ephemeral=True,
                )

                return

            embed = build_embed(
                base,
                historical,
            )

            await interaction.followup.send(
                embed=embed
            )

        except Exception as error:

            print(
                f"❌ VEYL Correlation error: "
                f"{error}"
            )

            await interaction.followup.send(
                (
                    "⚠️ VEYL Correlation a rencontré "
                    "une erreur pendant l'analyse."
                ),
                ephemeral=True,
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Correlation(bot)
    )

    print(
        "   ✓ commands.correlation"
    )