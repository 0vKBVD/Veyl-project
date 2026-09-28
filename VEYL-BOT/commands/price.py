import discord

from discord import app_commands
from discord.ext import commands

from services.market import get_crypto_price_async


# ============================================================
# VEYL PRICE ENGINE
# PREMIUM MARKET TOOL
# ============================================================


# ============================================================
# COINS
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


# ============================================================
# LOOKUPS
# ============================================================

COIN_BY_SYMBOL = {
    symbol.lower(): (
        coin_id,
        symbol,
        name,
        icon,
    )
    for coin_id, symbol, name, icon in COINS
}


COIN_BY_NAME = {
    name.lower(): (
        coin_id,
        symbol,
        name,
        icon,
    )
    for coin_id, symbol, name, icon in COINS
}


COIN_BY_ID = {
    coin_id.lower(): (
        coin_id,
        symbol,
        name,
        icon,
    )
    for coin_id, symbol, name, icon in COINS
}


# ============================================================
# FORMATTERS
# ============================================================

def format_price(value):

    if value is None:
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

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
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
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


def format_change(value):

    if value is None:
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    return f"{value:+.2f}%"


def change_icon(value):

    if value is None:
        return "○"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "○"

    if value > 0:
        return "▲"

    if value < 0:
        return "▼"

    return "◆"


def movement(value):

    if value is None:
        return "UNKNOWN"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value >= 5:
        return "STRONG UP"

    if value > 0:
        return "UP"

    if value <= -5:
        return "STRONG DOWN"

    if value < 0:
        return "DOWN"

    return "FLAT"


# ============================================================
# AUTOCOMPLETE
# ============================================================

async def crypto_autocomplete(
    interaction: discord.Interaction,
    current: str,
):

    current = (
        current.lower().strip()
        if current
        else ""
    )

    results = []

    for coin_id, symbol, name, icon in COINS:

        # ----------------------------------------------------
        # NOTHING TYPED
        # ----------------------------------------------------

        if not current:

            results.append(
                app_commands.Choice(
                    name=f"{icon} {symbol} — {name}",
                    value=symbol,
                )
            )

            continue

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

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
# RESOLVE COIN
# ============================================================

def resolve_coin(query):

    if not query:
        return None

    query = query.lower().strip()

    if not query:
        return None

    # --------------------------------------------------------
    # EXACT SYMBOL
    # --------------------------------------------------------

    if query in COIN_BY_SYMBOL:

        return COIN_BY_SYMBOL[query]

    # --------------------------------------------------------
    # EXACT NAME
    # --------------------------------------------------------

    if query in COIN_BY_NAME:

        return COIN_BY_NAME[query]

    # --------------------------------------------------------
    # EXACT COINGECKO ID
    # --------------------------------------------------------

    if query in COIN_BY_ID:

        return COIN_BY_ID[query]

    # --------------------------------------------------------
    # PARTIAL MATCH
    # --------------------------------------------------------

    for coin_id, symbol, name, icon in COINS:

        if (
            query in symbol.lower()
            or query in name.lower()
            or query in coin_id.lower()
        ):

            return (
                coin_id,
                symbol,
                name,
                icon,
            )

    return None


# ============================================================
# PRICE EMBED
# ============================================================

def build_price_embed(
    coin_id,
    symbol,
    name,
    icon,
    data,
):

    if not data:

        return build_error_embed(
            "DATA UNAVAILABLE",
            "VEYL could not retrieve live market data.",
        )

    # ========================================================
    # DATA
    # ========================================================

    current_price = data.get(
        "usd"
    )

    change_24h = data.get(
        "usd_24h_change"
    )

    market_cap = data.get(
        "usd_market_cap"
    )

    volume_24h = data.get(
        "usd_24h_vol"
    )

    last_updated = data.get(
        "last_updated_at"
    )

    # ========================================================
    # COLOR
    # ========================================================

    if change_24h is not None:

        try:

            change_value = float(
                change_24h
            )

        except (
            TypeError,
            ValueError
        ):

            change_value = 0

    else:

        change_value = 0

    if change_value > 0:

        embed_color = discord.Color.green()

    elif change_value < 0:

        embed_color = discord.Color.red()

    else:

        embed_color = discord.Color.blurple()

    # ========================================================
    # MOVEMENT
    # ========================================================

    direction = movement(
        change_24h
    )

    direction_icon = change_icon(
        change_24h
    )

    # ========================================================
    # EMBED
    # ========================================================

    embed = discord.Embed(
        title=f"⌘ VEYL // {symbol}",
        description=(
            "```text\n"
            "╔══════════════════════════════════════════╗\n"
            "║              VEYL PRICE                  ║\n"
            "║          MARKET DATA ENGINE              ║\n"
            "╚══════════════════════════════════════════╝\n"
            "```\n"
            f"{icon} **{name}**  •  `{symbol}`\n\n"
            f"## `{format_price(current_price)}`\n\n"
            f"{direction_icon} "
            f"**{format_change(change_24h)}**"
            f"  •  `{direction}`  •  `24H`"
        ),
        color=embed_color,
    )

    # ========================================================
    # PERFORMANCE
    # ========================================================

    embed.add_field(
        name="◈ PERFORMANCE",
        value=(
            f"**24H Change**\n"
            f"`{format_change(change_24h)}`\n\n"
            f"**Direction**\n"
            f"`{direction}`"
        ),
        inline=True,
    )

    # ========================================================
    # MARKET DATA
    # ========================================================

    embed.add_field(
        name="◈ MARKET DATA",
        value=(
            f"**Market Cap**\n"
            f"`{format_money(market_cap)}`\n\n"
            f"**24H Volume**\n"
            f"`{format_money(volume_24h)}`"
        ),
        inline=True,
    )

    # ========================================================
    # ENGINE
    # ========================================================

    embed.add_field(
        name="◈ VEYL ENGINE",
        value=(
            "◆ **PRICE**     `ONLINE`\n"
            "◆ **MARKET**    `ONLINE`\n"
            "◆ **CACHE**     `ACTIVE`\n"
            "◆ **API**       `CONNECTED`"
        ),
        inline=False,
    )

    # ========================================================
    # ASSET SNAPSHOT
    # ========================================================

    embed.add_field(
        name="▣ ASSET SNAPSHOT",
        value=(
            f"**Asset**\n"
            f"`{name}`\n\n"
            f"**Ticker**\n"
            f"`{symbol}`\n\n"
            f"**Source**\n"
            f"`CoinGecko`"
        ),
        inline=True,
    )

    # ========================================================
    # MARKET READ
    # ========================================================

    if change_24h is None:

        market_read = (
            "Market movement is currently unavailable."
        )

    elif change_value >= 5:

        market_read = (
            "Strong positive movement detected "
            "over the last 24 hours."
        )

    elif change_value > 0:

        market_read = (
            "Positive price movement detected "
            "over the last 24 hours."
        )

    elif change_value <= -5:

        market_read = (
            "Strong negative movement detected "
            "over the last 24 hours."
        )

    elif change_value < 0:

        market_read = (
            "Negative price movement detected "
            "over the last 24 hours."
        )

    else:

        market_read = (
            "Price is currently moving within "
            "a relatively flat 24H range."
        )

    embed.add_field(
        name="◆ VEYL MARKET READ",
        value=market_read,
        inline=True,
    )

    # ========================================================
    # SOURCE / UPDATE
    # ========================================================

    if last_updated:

        try:

            timestamp = int(
                last_updated
            )

            updated_text = (
                f"<t:{timestamp}:R>"
            )

        except (
            TypeError,
            ValueError
        ):

            updated_text = "LIVE"

    else:

        updated_text = "LIVE"

    embed.set_footer(
        text=(
            "VEYL • PRICE ENGINE • "
            f"MARKET DATA • {updated_text}"
        )
    )

    return embed


# ============================================================
# ERROR EMBED
# ============================================================

def build_error_embed(
    status="API REQUEST FAILED",
    message=(
        "VEYL could not retrieve live market data "
        "right now."
    ),
):

    embed = discord.Embed(
        title="⌘ VEYL // PRICE",
        description=(
            "```text\n"
            "PRICE ENGINE\n"
            "────────────────────────────────\n"
            f"STATUS     {status}\n"
            "DATA       UNAVAILABLE\n"
            "────────────────────────────────\n"
            "```\n"
            f"{message}\n\n"
            "VEYL will automatically use cached "
            "market data when available."
        ),
        color=discord.Color.red(),
    )

    embed.set_footer(
        text="VEYL • PRICE ENGINE • MARKET DATA"
    )

    return embed


# ============================================================
# COG
# ============================================================

class VeylPrice(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "💰 VEYL Price Engine activé."
        )

    # ========================================================
    # /PRICE
    # ========================================================

    @app_commands.command(
        name="price",
        description=(
            "Get live market data for a cryptocurrency."
        ),
    )
    @app_commands.describe(
        crypto="Choose a cryptocurrency.",
    )
    @app_commands.autocomplete(
        crypto=crypto_autocomplete
    )
    async def price(
        self,
        interaction: discord.Interaction,
        crypto: str,
    ):

        # ----------------------------------------------------
        # RESOLVE
        # ----------------------------------------------------

        resolved = resolve_coin(
            crypto
        )

        if resolved is None:

            embed = discord.Embed(
                title="⌘ VEYL // PRICE",
                description=(
                    "```text\n"
                    "PRICE ENGINE\n"
                    "────────────────────────────────\n"
                    "STATUS     INVALID ASSET\n"
                    "────────────────────────────────\n"
                    "```\n"
                    "❌ **Cryptocurrency not found.**\n\n"
                    "Use the autocomplete menu to select "
                    "a supported asset."
                ),
                color=discord.Color.red(),
            )

            embed.set_footer(
                text="VEYL • PRICE ENGINE"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        (
            coin_id,
            symbol,
            name,
            icon,
        ) = resolved

        # ----------------------------------------------------
        # DEFER
        # ----------------------------------------------------

        await interaction.response.defer()

        # ----------------------------------------------------
        # CENTRAL MARKET ENGINE
        # ----------------------------------------------------
        #
        # IMPORTANT:
        #
        # No direct CoinGecko request here.
        #
        # Everything goes through:
        #
        # services.market
        #
        # which handles:
        #   • cache
        #   • rate limit
        #   • 429
        #   • retry
        #   • stale data
        #   • shared session
        #   • request locking
        #
        # ----------------------------------------------------

        data = await get_crypto_price_async(
            coin_id
        )

        # ----------------------------------------------------
        # NO DATA
        # ----------------------------------------------------

        if not data:

            await interaction.followup.send(
                embed=build_error_embed(
                    "MARKET DATA UNAVAILABLE",
                    (
                        "VEYL could not retrieve "
                        f"live data for **{name}**.\n\n"
                        "CoinGecko may be temporarily "
                        "rate-limited. VEYL has protected "
                        "the rest of the system from the "
                        "request failure."
                    ),
                )
            )

            return

        # ----------------------------------------------------
        # BUILD EMBED
        # ----------------------------------------------------

        embed = build_price_embed(
            coin_id=coin_id,
            symbol=symbol,
            name=name,
            icon=icon,
            data=data,
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

async def setup(
    bot
):

    await bot.add_cog(
        VeylPrice(bot)
    )

    print(
        "   ✅ commands.price"
    )