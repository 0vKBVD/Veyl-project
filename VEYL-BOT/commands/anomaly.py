import asyncio
import time

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# VEYL ANOMALY ENGINE
# PHASE 2 — MARKET ANOMALY DETECTION
# ============================================================

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

REQUEST_TIMEOUT = 10

ANOMALY_COOLDOWN = 30

ANOMALY_COINS = [
    ("bitcoin", "BTC"),
    ("ethereum", "ETH"),
    ("solana", "SOL"),
    ("binancecoin", "BNB"),
    ("ripple", "XRP"),
    ("dogecoin", "DOGE"),
    ("cardano", "ADA"),
    ("avalanche-2", "AVAX"),
    ("chainlink", "LINK"),
    ("shiba-inu", "SHIB"),
    ("tron", "TRX"),
    ("polkadot", "DOT"),
    ("litecoin", "LTC"),
    ("uniswap", "UNI"),
    ("sui", "SUI"),
    ("arbitrum", "ARB"),
    ("optimism", "OP"),
    ("pepe", "PEPE"),
]


# ============================================================
# API
# ============================================================

async def get_anomaly_data():

    ids = ",".join(
        coin_id
        for coin_id, _ in ANOMALY_COINS
    )

    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    headers = {
        "User-Agent": "VEYL-Anomaly/1.0"
    }

    try:

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        ) as session:

            async with session.get(
                COINGECKO_URL,
                params=params,
            ) as response:

                if response.status == 429:

                    print(
                        "⚠️ VEYL Anomaly : "
                        "CoinGecko HTTP 429."
                    )

                    return None

                if response.status != 200:

                    print(
                        f"⚠️ VEYL Anomaly : "
                        f"CoinGecko HTTP {response.status}."
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        print(
            "⚠️ VEYL Anomaly : API timeout."
        )

        return None

    except Exception as error:

        print(
            f"❌ VEYL Anomaly API error : {error}"
        )

        return None


# ============================================================
# HELPERS
# ============================================================

def clamp(
    value,
    minimum=0,
    maximum=100,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def format_price(value):

    if value is None:
        return "—"

    if value >= 1000:
        return f"${value:,.0f}"

    if value >= 1:
        return f"${value:,.2f}"

    if value >= 0.01:
        return f"${value:,.4f}"

    return f"${value:,.8f}"


def format_money(value):

    if value is None:
        return "—"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.2f}K"

    return f"${value:,.0f}"


def score_bar(
    score,
    length=10,
):

    score = clamp(score)

    filled = round(
        score / 100 * length
    )

    return (
        "█" * filled
        + "░" * (length - filled)
    )


# ============================================================
# MARKET BASELINE
# ============================================================

def calculate_market_average(data):

    changes = []

    for coin_id, _ in ANOMALY_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is not None:
            changes.append(change)

    if not changes:
        return 0

    return sum(changes) / len(changes)


# ============================================================
# VOLUME BASELINE
# ============================================================

def calculate_volume_average(data):

    volumes = []

    for coin_id, _ in ANOMALY_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        volume = coin.get(
            "usd_24h_vol"
        )

        if volume:
            volumes.append(volume)

    if not volumes:
        return 0

    return sum(volumes) / len(volumes)


# ============================================================
# PRICE ANOMALY
# ============================================================

def detect_price_anomaly(
    symbol,
    coin,
    market_average,
):

    change = coin.get(
        "usd_24h_change"
    )

    if change is None:
        return None

    absolute_change = abs(change)

    # Mouvement supérieur à 5%
    if absolute_change >= 5:

        strength = clamp(
            absolute_change * 10
        )

        direction = (
            "UP"
            if change > 0
            else "DOWN"
        )

        emoji = (
            "📈"
            if change > 0
            else "📉"
        )

        return {
            "type": "PRICE SPIKE",
            "symbol": symbol,
            "emoji": emoji,
            "direction": direction,
            "value": change,
            "score": round(strength),
            "description": (
                f"{symbol} moved "
                f"{change:+.2f}% in 24H."
            ),
        }

    return None


# ============================================================
# MARKET DIVERGENCE
# ============================================================

def detect_divergence(
    symbol,
    coin,
    market_average,
):

    change = coin.get(
        "usd_24h_change"
    )

    if change is None:
        return None

    divergence = (
        change
        - market_average
    )

    if abs(divergence) < 4:

        return None

    score = clamp(
        abs(divergence) * 12
    )

    if divergence > 0:

        description = (
            f"{symbol} is outperforming "
            f"the broader tracked market "
            f"by {divergence:+.2f}%."
        )

        emoji = "🚀"

    else:

        description = (
            f"{symbol} is underperforming "
            f"the broader tracked market "
            f"by {divergence:.2f}%."
        )

        emoji = "⚠️"

    return {
        "type": "MARKET DIVERGENCE",
        "symbol": symbol,
        "emoji": emoji,
        "direction": (
            "OUTPERFORMING"
            if divergence > 0
            else "UNDERPERFORMING"
        ),
        "value": divergence,
        "score": round(score),
        "description": description,
    }


# ============================================================
# VOLUME ANOMALY
# ============================================================

def detect_volume_anomaly(
    symbol,
    coin,
    average_volume,
):

    volume = coin.get(
        "usd_24h_vol"
    )

    if not volume or average_volume <= 0:

        return None

    ratio = (
        volume
        / average_volume
    )

    # Volume au moins 2x supérieur
    # à la moyenne des actifs suivis.

    if ratio < 2:

        return None

    excess_percentage = (
        ratio - 1
    ) * 100

    score = clamp(
        excess_percentage * 0.7
    )

    return {
        "type": "VOLUME ANOMALY",
        "symbol": symbol,
        "emoji": "📊",
        "direction": "HIGH VOLUME",
        "value": excess_percentage,
        "score": round(score),
        "description": (
            f"{symbol} volume is "
            f"{excess_percentage:+.0f}% "
            f"above the tracked baseline."
        ),
    }


# ============================================================
# MOMENTUM SHOCK
# ============================================================

def detect_momentum_shock(
    symbol,
    coin,
):

    change = coin.get(
        "usd_24h_change"
    )

    if change is None:
        return None

    absolute_change = abs(change)

    if absolute_change < 8:

        return None

    score = clamp(
        absolute_change * 8
    )

    if change > 0:

        emoji = "⚡"
        direction = "POSITIVE SHOCK"

    else:

        emoji = "🔻"
        direction = "NEGATIVE SHOCK"

    return {
        "type": "MOMENTUM SHOCK",
        "symbol": symbol,
        "emoji": emoji,
        "direction": direction,
        "value": change,
        "score": round(score),
        "description": (
            f"{symbol} registered an "
            f"extreme 24H movement of "
            f"{change:+.2f}%."
        ),
    }


# ============================================================
# ANALYZE
# ============================================================

def analyze_anomalies(data):

    market_average = (
        calculate_market_average(
            data
        )
    )

    average_volume = (
        calculate_volume_average(
            data
        )
    )

    anomalies = []

    for coin_id, symbol in ANOMALY_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        detectors = [
            detect_price_anomaly(
                symbol,
                coin,
                market_average,
            ),
            detect_divergence(
                symbol,
                coin,
                market_average,
            ),
            detect_volume_anomaly(
                symbol,
                coin,
                average_volume,
            ),
            detect_momentum_shock(
                symbol,
                coin,
            ),
        ]

        for anomaly in detectors:

            if anomaly:

                anomalies.append(
                    anomaly
                )

    # Plus gros signaux en premier
    anomalies.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return {
        "market_average": market_average,
        "average_volume": average_volume,
        "anomalies": anomalies,
    }


# ============================================================
# EMBED
# ============================================================

def build_anomaly_embed(
    data,
    analysis,
):

    now = time.strftime(
        "%H:%M:%S"
    )

    anomalies = analysis[
        "anomalies"
    ]

    embed = discord.Embed(
        title="⚠️  VEYL // ANOMALY ENGINE",
        description=(
            "```text\n"
            "╔══════════════════════════════════════════════╗\n"
            "║             VEYL ANOMALY ENGINE             ║\n"
            "║       UNUSUAL MARKET ACTIVITY DETECTOR      ║\n"
            "╚══════════════════════════════════════════════╝\n"
            "```\n"
            f"**ENGINE STATUS**  🟢 LIVE\n"
            f"**SCAN TIME**  `{now}`\n"
            f"**ANOMALIES DETECTED**  "
            f"`{len(anomalies)}`"
        ),
        color=discord.Color.orange(),
    )

    # ========================================================
    # TOP ANOMALIES
    # ========================================================

    if anomalies:

        top_text = ""

        for index, anomaly in enumerate(
            anomalies[:8],
            start=1,
        ):

            top_text += (
                f"`{index}` "
                f"{anomaly['emoji']} "
                f"**{anomaly['symbol']}** "
                f"`{anomaly['type']}`\n"
                f"   {anomaly['description']}\n"
                f"   Confidence "
                f"`{anomaly['score']}%`\n\n"
            )

    else:

        top_text = (
            "🟢 **NO SIGNIFICANT ANOMALIES**\n\n"
            "Market activity remains "
            "within the current detection "
            "thresholds."
        )

    embed.add_field(
        name="⚠ ACTIVE ANOMALIES",
        value=top_text[:1024],
        inline=False,
    )

    # ========================================================
    # SIGNAL TYPES
    # ========================================================

    price_spikes = sum(
        1
        for anomaly in anomalies
        if anomaly["type"] == "PRICE SPIKE"
    )

    volume_anomalies = sum(
        1
        for anomaly in anomalies
        if anomaly["type"] == "VOLUME ANOMALY"
    )

    divergences = sum(
        1
        for anomaly in anomalies
        if anomaly["type"] == "MARKET DIVERGENCE"
    )

    momentum_shocks = sum(
        1
        for anomaly in anomalies
        if anomaly["type"] == "MOMENTUM SHOCK"
    )

    signal_types = (
        f"📈 **PRICE SPIKES**  `{price_spikes}`\n"
        f"📊 **VOLUME ANOMALIES**  `{volume_anomalies}`\n"
        f"🌐 **DIVERGENCES**  `{divergences}`\n"
        f"⚡ **MOMENTUM SHOCKS**  `{momentum_shocks}`"
    )

    embed.add_field(
        name="◈ DETECTION MATRIX",
        value=signal_types,
        inline=True,
    )

    # ========================================================
    # MARKET BASELINE
    # ========================================================

    baseline = (
        f"**Tracked Market Average**\n"
        f"`{analysis['market_average']:+.2f}%`\n\n"

        f"**Average 24H Volume**\n"
        f"`{format_money(analysis['average_volume'])}`\n\n"

        f"**Assets Scanned**\n"
        f"`{len(ANOMALY_COINS)}`"
    )

    embed.add_field(
        name="◈ MARKET BASELINE",
        value=baseline,
        inline=True,
    )

    # ========================================================
    # TOP SIGNAL
    # ========================================================

    if anomalies:

        strongest = anomalies[0]

        strongest_text = (
            f"{strongest['emoji']} "
            f"**{strongest['type']}**\n\n"
            f"Asset: **{strongest['symbol']}**\n"
            f"Direction: "
            f"`{strongest['direction']}`\n"
            f"Deviation: "
            f"`{strongest['value']:+.2f}%`\n\n"
            f"Confidence\n"
            f"`{score_bar(strongest['score'])}` "
            f"**{strongest['score']}%**"
        )

    else:

        strongest_text = (
            "No dominant anomaly detected."
        )

    embed.add_field(
        name="🎯 STRONGEST SIGNAL",
        value=strongest_text,
        inline=False,
    )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    embed.add_field(
        name="ℹ VEYL ENGINE",
        value=(
            "Anomalies indicate unusual market "
            "conditions based on available data. "
            "They are **not price predictions "
            "or financial advice**."
        ),
        inline=False,
    )

    embed.set_footer(
        text=(
            "VEYL • ANOMALY ENGINE • PHASE 2 "
            "• Experimental market intelligence"
        )
    )

    return embed


# ============================================================
# VIEW
# ============================================================

class AnomalyView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.last_refresh = 0

    @discord.ui.button(
        label="Refresh Scan",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_anomaly_refresh",
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        current_time = time.time()

        if (
            current_time - self.last_refresh
            < ANOMALY_COOLDOWN
        ):

            remaining = int(
                ANOMALY_COOLDOWN
                - (
                    current_time
                    - self.last_refresh
                )
            ) + 1

            await interaction.response.send_message(
                f"⏳ New anomaly scan available "
                f"in **{remaining}s**.",
                ephemeral=True,
            )

            return

        self.last_refresh = current_time

        await interaction.response.defer()

        data = await get_anomaly_data()

        if data is None:

            await interaction.followup.send(
                "⚠️ VEYL Anomaly Engine "
                "could not retrieve market data.",
                ephemeral=True,
            )

            return

        analysis = analyze_anomalies(
            data
        )

        embed = build_anomaly_embed(
            data,
            analysis,
        )

        try:

            await interaction.message.edit(
                embed=embed,
                view=self,
            )

        except discord.HTTPException as error:

            print(
                f"⚠️ VEYL Anomaly Discord error : "
                f"{error}"
            )


# ============================================================
# COG
# ============================================================

class VeylAnomaly(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        print(
            "⚠️ VEYL Anomaly Engine activé."
        )

    # ========================================================
    # /ANOMALIES
    # ========================================================

    @app_commands.command(
        name="anomalies",
        description=(
            "Scan the market for unusual activity."
        ),
    )
    async def anomalies(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer()

        data = await get_anomaly_data()

        if data is None:

            await interaction.followup.send(
                "⚠️ VEYL Anomaly Engine could "
                "not retrieve market data.",
                ephemeral=True,
            )

            return

        analysis = analyze_anomalies(
            data
        )

        embed = build_anomaly_embed(
            data,
            analysis,
        )

        view = AnomalyView()

        view.last_refresh = time.time()

        await interaction.followup.send(
            embed=embed,
            view=view,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylAnomaly(bot)
    )

    print(
        "   ✅ commands.anomaly"
    )