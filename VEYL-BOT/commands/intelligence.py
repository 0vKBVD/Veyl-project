import asyncio
import discord

from discord import app_commands
from discord.ext import commands

from services.market import get_crypto_price_async


# ============================================================
# VEYL INTELLIGENCE
# ============================================================

print(">>> INTELLIGENCE.PY CHARGÉ")


# ============================================================
# SUPPORTED ASSETS
# ============================================================

COINS = [
    ("bitcoin", "BTC", "Bitcoin", "₿"),
    ("ethereum", "ETH", "Ethereum", "Ξ"),
    ("tether", "USDT", "Tether", "₮"),
    ("binancecoin", "BNB", "BNB", "◆"),
    ("solana", "SOL", "Solana", "◎"),
    ("usd-coin", "USDC", "USD Coin", "$"),
    ("ripple", "XRP", "XRP", "✕"),
    ("dogecoin", "DOGE", "Dogecoin", "Ð"),
    ("cardano", "ADA", "Cardano", "₳"),
    ("avalanche-2", "AVAX", "Avalanche", "▲"),
    ("chainlink", "LINK", "Chainlink", "⬡"),
    ("shiba-inu", "SHIB", "Shiba Inu", "◆"),
    ("tron", "TRX", "TRON", "◆"),
    ("polkadot", "DOT", "Polkadot", "●"),
    ("litecoin", "LTC", "Litecoin", "Ł"),
    ("uniswap", "UNI", "Uniswap", "◆"),
    ("sui", "SUI", "Sui", "◆"),
    ("arbitrum", "ARB", "Arbitrum", "◆"),
    ("optimism", "OP", "Optimism", "◆"),
    ("pepe", "PEPE", "Pepe", "◆"),
    ("near", "NEAR", "NEAR Protocol", "◆"),
    ("internet-computer", "ICP", "Internet Computer", "◆"),
    ("aptos", "APT", "Aptos", "◆"),
    ("cosmos", "ATOM", "Cosmos", "⚛"),
    ("filecoin", "FIL", "Filecoin", "◆"),
]


COIN_BY_QUERY = {}

for coin_id, symbol, name, icon in COINS:

    COIN_BY_QUERY[coin_id.lower()] = (
        coin_id,
        symbol,
        name,
        icon,
    )

    COIN_BY_QUERY[symbol.lower()] = (
        coin_id,
        symbol,
        name,
        icon,
    )

    COIN_BY_QUERY[name.lower()] = (
        coin_id,
        symbol,
        name,
        icon,
    )


# ============================================================
# FORMATTERS
# ============================================================

def format_price(value):

    if value is None:
        return "N/A"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if value >= 1_000_000:
        return f"${value:,.0f}"

    if value >= 1_000:
        return f"${value:,.2f}"

    if value >= 1:
        return f"${value:,.4f}"

    if value >= 0.01:
        return f"${value:,.5f}"

    return f"${value:,.8f}"


def format_money(value):

    if value is None:
        return "N/A"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.2f}K"

    return f"${value:,.0f}"


def format_percent(value):

    if value is None:
        return "N/A"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"

    return f"{value:+.2f}%"


def progress_bar(value, length=12):

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0

    value = max(0, min(100, value))

    filled = round(
        (value / 100) * length
    )

    return (
        "█" * filled
        + "░" * (length - filled)
    )


def sentiment_from_score(score):

    if score >= 75:
        return "BULLISH"

    if score >= 55:
        return "SLIGHTLY BULLISH"

    if score >= 45:
        return "NEUTRAL"

    if score >= 25:
        return "SLIGHTLY BEARISH"

    return "BEARISH"


def movement_from_changes(
    change_1h,
    change_24h,
    change_7d
):

    values = [
        value
        for value in (
            change_1h,
            change_24h,
            change_7d
        )
        if value is not None
    ]

    if not values:
        return "UNKNOWN"

    positive = sum(
        1
        for value in values
        if value > 0
    )

    negative = sum(
        1
        for value in values
        if value < 0
    )

    if positive == len(values):
        return "STRONG"

    if negative == len(values):
        return "WEAK"

    return "MIXED"


# ============================================================
# SCORE
# ============================================================

def calculate_asset_score(
    change_1h,
    change_24h,
    change_7d
):

    score = 50.0

    if change_1h is not None:

        if change_1h > 1:
            score += 10

        elif change_1h < -1:
            score -= 10

    if change_24h is not None:

        score += max(
            -20,
            min(
                20,
                change_24h * 2
            )
        )

    if change_7d is not None:

        score += max(
            -15,
            min(
                15,
                change_7d
            )
        )

    return max(
        0,
        min(
            100,
            score
        )
    )


# ============================================================
# AUTOCOMPLETE
# ============================================================

async def intelligence_autocomplete(
    interaction: discord.Interaction,
    current: str,
):

    current = (
        current.lower().strip()
        if current
        else ""
    )

    results = []

    # --------------------------------------------------------
    # NOTHING TYPED
    # --------------------------------------------------------

    if not current:

        for coin_id, symbol, name, icon in COINS:

            results.append(
                app_commands.Choice(
                    name=f"{icon} {symbol} — {name}",
                    value=symbol,
                )
            )

        return results[:25]

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    for coin_id, symbol, name, icon in COINS:

        if (
            current in symbol.lower()
            or current in name.lower()
            or current in coin_id.lower()
        ):

            results.append(
                app_commands.Choice(
                    name=f"{icon} {symbol} — {name}",
                    value=symbol,
                )
            )

    return results[:25]


# ============================================================
# RESOLVE
# ============================================================

def resolve_coin(query):

    if not query:
        return None

    query = query.lower().strip()

    if not query:
        return None

    if query in COIN_BY_QUERY:

        return COIN_BY_QUERY[query]

    for coin_id, symbol, name, icon in COINS:

        if (
            query in coin_id.lower()
            or query in symbol.lower()
            or query in name.lower()
        ):

            return (
                coin_id,
                symbol,
                name,
                icon,
            )

    return None


# ============================================================
# ERROR EMBED
# ============================================================

def unavailable_embed(
    asset_name="market"
):

    embed = discord.Embed(
        title="◈ VEYL / INTELLIGENCE",
        description=(
            "### MARKET DATA TEMPORARILY UNAVAILABLE\n\n"
            f"VEYL could not retrieve market data for "
            f"**{asset_name}** right now.\n\n"
            "`No request will be retried aggressively.`\n\n"
            "The request has been routed through the "
            "central VEYL Market Engine. Its cache and "
            "rate-limit protection remain active."
        ),
        color=0xF2F2F2
    )

    embed.add_field(
        name="◈ ENGINE STATUS",
        value=(
            "◆ **MARKET ENGINE**  `ONLINE`\n"
            "◆ **RATE LIMIT**     `PROTECTED`\n"
            "◆ **CACHE**          `ACTIVE`\n"
            "◆ **REQUEST**        `BLOCKED SAFELY`"
        ),
        inline=False
    )

    embed.set_footer(
        text=(
            "VEYL • INTELLIGENCE • "
            "RATE-LIMIT PROTECTION ACTIVE"
        )
    )

    return embed


# ============================================================
# INTELLIGENCE EMBED
# ============================================================

def build_intelligence_embed(
    coin_id,
    symbol,
    name,
    icon,
    data
):

    price = data.get(
        "usd"
    )

    change_24h = data.get(
        "usd_24h_change"
    )

    market_cap = data.get(
        "usd_market_cap"
    )

    volume = data.get(
        "usd_24h_vol"
    )

    change_1h = data.get(
        "usd_1h_change"
    )

    change_7d = data.get(
        "usd_7d_change"
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = calculate_asset_score(
        change_1h,
        change_24h,
        change_7d
    )

    sentiment = sentiment_from_score(
        score
    )

    movement = movement_from_changes(
        change_1h,
        change_24h,
        change_7d
    )

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    if score >= 70:

        color = 0xF2F2F2

    elif score <= 35:

        color = 0x555555

    else:

        color = 0x8A8A8A

    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = discord.Embed(
        title="◈ VEYL / INTELLIGENCE",
        description=(
            f"{icon} **{name.upper()}**  "
            f"`{symbol}`\n"
            "Digital asset intelligence terminal\n\n"
            f"## `{format_price(price)}`"
        ),
        color=color
    )

    # --------------------------------------------------------
    # SENTIMENT
    # --------------------------------------------------------

    embed.add_field(
        name="MARKET SENTIMENT",
        value=(
            f"**{sentiment}**\n"
            f"`{progress_bar(score)} "
            f"{score:.0f}/100`"
        ),
        inline=False
    )

    # --------------------------------------------------------
    # MARKET STRUCTURE
    # --------------------------------------------------------

    embed.add_field(
        name="MARKET STRUCTURE",
        value=(
            f"**Price**\n"
            f"{format_price(price)}\n\n"
            f"**Market Cap**\n"
            f"{format_money(market_cap)}"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    embed.add_field(
        name="MOMENTUM",
        value=(
            f"**1H**  {format_percent(change_1h)}\n"
            f"**24H** {format_percent(change_24h)}\n"
            f"**7D**  {format_percent(change_7d)}\n\n"
            f"**REGIME**\n"
            f"{movement}"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    embed.add_field(
        name="LIQUIDITY",
        value=(
            f"24H Volume\n"
            f"**{format_money(volume)}**"
        ),
        inline=False
    )

    # --------------------------------------------------------
    # VEYL SIGNAL
    # --------------------------------------------------------

    embed.add_field(
        name="VEYL SIGNAL",
        value=(
            f"`SCORE`      **{score:.0f}/100**\n"
            f"`MOMENTUM`   **{movement}**\n"
            f"`SENTIMENT`  **{sentiment}**"
        ),
        inline=False
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    embed.set_footer(
        text=(
            "VEYL INTELLIGENCE • "
            "CENTRAL MARKET ENGINE • CACHE PROTECTED"
        )
    )

    return embed


# ============================================================
# COG
# ============================================================

class VeylIntelligence(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        print(
            "🧠 VEYL Intelligence Engine activé."
        )

    # ========================================================
    # /INTELLIGENCE
    # ========================================================

    @app_commands.command(
        name="intelligence",
        description=(
            "VEYL Intelligence — analyze a cryptocurrency."
        )
    )
    @app_commands.describe(
        asset=(
            "Choose a cryptocurrency."
        )
    )
    @app_commands.autocomplete(
        asset=intelligence_autocomplete
    )
    async def intelligence(
        self,
        interaction: discord.Interaction,
        asset: str
    ):

        # ----------------------------------------------------
        # RESOLVE
        # ----------------------------------------------------

        resolved = resolve_coin(
            asset
        )

        if resolved is None:

            await interaction.response.send_message(
                embed=unavailable_embed(
                    asset
                ),
                ephemeral=True
            )

            return

        (
            coin_id,
            symbol,
            name,
            icon,
        ) = resolved

        # ----------------------------------------------------
        # RESPOND IMMEDIATELY
        # ----------------------------------------------------

        await interaction.response.defer()

        try:

            # ------------------------------------------------
            # CENTRAL VEYL MARKET ENGINE
            # ------------------------------------------------

            data = await asyncio.wait_for(
                get_crypto_price_async(
                    coin_id
                ),
                timeout=20
            )

        except asyncio.TimeoutError:

            print(
                f"⏳ Intelligence timeout • {symbol}"
            )

            await interaction.followup.send(
                embed=unavailable_embed(
                    name
                )
            )

            return

        except Exception as error:

            print(
                f"❌ Intelligence error • "
                f"{type(error).__name__}: {error}"
            )

            await interaction.followup.send(
                embed=unavailable_embed(
                    name
                )
            )

            return

        # ----------------------------------------------------
        # NO DATA
        # ----------------------------------------------------

        if not data:

            print(
                f"⚠️ Intelligence : "
                f"aucune donnée • {symbol}"
            )

            await interaction.followup.send(
                embed=unavailable_embed(
                    name
                )
            )

            return

        # ----------------------------------------------------
        # NORMALIZE CENTRAL ENGINE DATA
        # ----------------------------------------------------

        normalized = {
            "usd": data.get("usd"),
            "usd_24h_change": data.get(
                "usd_24h_change"
            ),
            "usd_market_cap": data.get(
                "usd_market_cap"
            ),
            "usd_24h_vol": data.get(
                "usd_24h_vol"
            ),
            "usd_1h_change": data.get(
                "usd_1h_change"
            ),
            "usd_7d_change": data.get(
                "usd_7d_change"
            ),
        }

        # ----------------------------------------------------
        # BUILD
        # ----------------------------------------------------

        embed = build_intelligence_embed(
            coin_id=coin_id,
            symbol=symbol,
            name=name,
            icon=icon,
            data=normalized
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        await interaction.followup.send(
            embed=embed
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylIntelligence(bot)
    )

    print(
        "   └─ commands.intelligence chargé"
    )