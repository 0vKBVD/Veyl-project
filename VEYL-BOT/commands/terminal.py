# ============================================================
# VEYL TERMINAL 10.1
# INSTITUTIONAL MARKET INTELLIGENCE SYSTEM
#
# Centralized:
#   services.market
#   services.charts
#
# Binance / CoinGecko handled by services layer.
# Terminal never calls APIs directly.
# ============================================================

import time

import discord
from discord import app_commands
from discord.ext import commands

from services.market import (
    COINS,
    get_market_data,
    find_coin,
)

from services.charts import (
    create_chart,
    MATPLOTLIB_AVAILABLE,
)


# ============================================================
# CONFIGURATION
# ============================================================

TERMINAL_CHANNEL = "veyl-terminal"

REFRESH_COOLDOWN = 10

EMBED_COLOR = 0x18191C


# ============================================================
# FORMATTERS
# ============================================================

def price(value):

    if value is None:
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    if value >= 1000:
        return f"${value:,.0f}"

    if value >= 1:
        return f"${value:,.2f}"

    if value >= 0.01:
        return f"${value:,.4f}"

    return f"${value:,.8f}"


def money(value):

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


def pct(value):

    if value is None:
        return "—"

    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "—"


def direction(value):

    if value is None:
        return "·"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "·"

    if value > 0:
        return "▲"

    if value < 0:
        return "▼"

    return "·"


def bar(score, length=18):

    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0

    score = max(0, min(100, score))

    filled = round(
        score / 100 * length
    )

    return (
        "█" * filled
        + "░" * (length - filled)
    )


def timestamp():

    return time.strftime("%H:%M:%S")


# ============================================================
# EMBED FACTORY
# ============================================================

def terminal_embed(
    title,
    description=None,
):

    return discord.Embed(
        title=title,
        description=description,
        color=EMBED_COLOR,
    )


def footer(embed, section):

    embed.set_footer(
        text=(
            f"VEYL • {section}"
            f" • {timestamp()}"
        )
    )


# ============================================================
# OFFLINE / EMPTY COCKPIT
# ============================================================

def build_offline_cockpit():

    embed = terminal_embed(
        "⌘ VEYL / TERMINAL 10.1",
        (
            "```text\n"
            "╔════════════════════════════════════════════╗\n"
            "║                 V E Y L                    ║\n"
            "║          MARKET INTELLIGENCE               ║\n"
            "║              TERMINAL 10.1                 ║\n"
            "╠════════════════════════════════════════════╣\n"
            "║ MARKET   CHART   BRAIN   SIGNALS            ║\n"
            "║ FLOW     NEWS    ANOMALIES   SYSTEM         ║\n"
            "╚════════════════════════════════════════════╝\n"
            "```\n"
            "`TERMINAL ONLINE`  `MARKET DATA LIMITED`"
        ),
    )

    embed.add_field(
        name="▣ CORE MARKET",
        value=(
            "`BTC`  **—**\n"
            "`ETH`  **—**\n"
            "`SOL`  **—**"
        ),
        inline=True,
    )

    embed.add_field(
        name="⌘ INTELLIGENCE",
        value=(
            "BRAIN       `ONLINE`\n"
            "SIGNALS     `ONLINE`\n"
            "ANOMALIES   `ONLINE`\n"
            "MEMORY      `ONLINE`\n"
            "FLOW        `ONLINE`"
        ),
        inline=True,
    )

    embed.add_field(
        name="DATA STATUS",
        value=(
            "MARKET      `WAITING`\n"
            "CHART       "
            f"`{'ONLINE' if MATPLOTLIB_AVAILABLE else 'OFFLINE'}`\n"
            "CACHE       `ACTIVE`\n"
            "ENGINE      `ONLINE`"
        ),
        inline=True,
    )

    embed.add_field(
        name="SYSTEM",
        value=(
            "TERMINAL CORE   `ONLINE`\n"
            "MARKET ENGINE   `ONLINE`\n"
            "CHART ENGINE    "
            f"`{'ONLINE' if MATPLOTLIB_AVAILABLE else 'OFFLINE'}`\n"
            "CACHE LAYER     `ONLINE`"
        ),
        inline=True,
    )

    embed.add_field(
        name="STATUS",
        value=(
            "The terminal interface is operational.\n"
            "Market providers are temporarily unavailable "
            "or rate-limited.\n\n"
            "Use **REFRESH** to retry."
        ),
        inline=False,
    )

    footer(
        embed,
        "TERMINAL • DEGRADED MODE",
    )

    return embed


# ============================================================
# COCKPIT
# ============================================================

def build_cockpit(data):

    if not isinstance(data, dict):
        return build_offline_cockpit()

    btc = data.get("bitcoin") or {}
    eth = data.get("ethereum") or {}
    sol = data.get("solana") or {}

    btc_change = btc.get("usd_24h_change") or 0
    eth_change = eth.get("usd_24h_change") or 0
    sol_change = sol.get("usd_24h_change") or 0

    average = (
        btc_change
        + eth_change
        + sol_change
    ) / 3

    if average >= 2:
        market_signal = "BULLISH"
    elif average >= 0:
        market_signal = "POSITIVE"
    elif average > -2:
        market_signal = "CAUTIOUS"
    else:
        market_signal = "BEARISH"

    positive = 0
    negative = 0
    neutral = 0

    for coin_id, _, _ in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is None:
            continue

        if change > 0:
            positive += 1
        elif change < 0:
            negative += 1
        else:
            neutral += 1

    total = positive + negative + neutral

    breadth_pct = (
        positive / total * 100
        if total
        else 0
    )

    embed = terminal_embed(
        "⌘ VEYL / TERMINAL 10.1",
        (
            "```text\n"
            "╔════════════════════════════════════════════╗\n"
            "║                 V E Y L                    ║\n"
            "║          MARKET INTELLIGENCE               ║\n"
            "║              TERMINAL 10.1                 ║\n"
            "╠════════════════════════════════════════════╣\n"
            "║ MARKET   CHART   BRAIN   SIGNALS            ║\n"
            "║ FLOW     NEWS    ANOMALIES   SYSTEM         ║\n"
            "╚════════════════════════════════════════════╝\n"
            "```\n"
            f"`LIVE`  "
            f"`MARKET {market_signal}`  "
            f"`{timestamp()}`"
        ),
    )

    core = (
        f"`BTC`  **{price(btc.get('usd'))}**  "
        f"`{pct(btc_change)}`\n"
        f"`ETH`  **{price(eth.get('usd'))}**  "
        f"`{pct(eth_change)}`\n"
        f"`SOL`  **{price(sol.get('usd'))}**  "
        f"`{pct(sol_change)}`"
    )

    embed.add_field(
        name="▣ CORE MARKET",
        value=core,
        inline=True,
    )

    intelligence = (
        "BRAIN       `ONLINE`\n"
        "SIGNALS     `ONLINE`\n"
        "ANOMALIES   `ONLINE`\n"
        "MEMORY      `ONLINE`\n"
        "FLOW        `ONLINE`"
    )

    embed.add_field(
        name="⌘ INTELLIGENCE",
        value=intelligence,
        inline=True,
    )

    breadth = (
        f"UP          `{positive}`\n"
        f"DOWN        `{negative}`\n"
        f"FLAT        `{neutral}`\n\n"
        f"**Breadth**\n"
        f"`{breadth_pct:.0f}% positive`\n\n"
        f"`{market_signal}`"
    )

    embed.add_field(
        name="MARKET BREADTH",
        value=breadth,
        inline=True,
    )

    quick = (
        f"**BTC** `{btc_change:+.2f}%`\n"
        f"**ETH** `{eth_change:+.2f}%`\n"
        f"**SOL** `{sol_change:+.2f}%`\n\n"
        f"**MARKET BIAS**\n"
        f"`{market_signal}`"
    )

    embed.add_field(
        name="◈ QUICK READ",
        value=quick,
        inline=True,
    )

    data_status = (
        "SOURCE          `MULTI-PROVIDER`\n"
        f"ASSETS          `{len(COINS)}`\n"
        "WINDOW          `24H`\n"
        "CACHE           `ACTIVE`\n"
        "MODE            `LIVE`\n"
        f"UPDATE          `{timestamp()}`"
    )

    embed.add_field(
        name="DATA STATUS",
        value=data_status,
        inline=True,
    )

    system = (
        "TERMINAL CORE   `ONLINE`\n"
        "MARKET ENGINE   `ONLINE`\n"
        "CHART ENGINE    "
        f"`{'ONLINE' if MATPLOTLIB_AVAILABLE else 'OFFLINE'}`\n"
        "BRAIN ENGINE    `ONLINE`\n"
        "CACHE LAYER     `ONLINE`"
    )

    embed.add_field(
        name="SYSTEM",
        value=system,
        inline=True,
    )

    embed.add_field(
        name="VEYL ARCHITECTURE",
        value=(
            "`MARKET` → `BRAIN` → `SIGNALS`\n"
            "`FLOW` + `NEWS` → `ANOMALIES`\n"
            "`SIGNALS` + `ANOMALIES` → `MEMORY`\n"
            "`MEMORY` → `AUTOMATION`"
        ),
        inline=False,
    )

    footer(
        embed,
        "INTELLIGENCE TERMINAL",
    )

    return embed


# ============================================================
# MARKET VIEW
# ============================================================

def build_market_view(data):

    movers = []

    for coin_id, symbol, name in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is None:
            continue

        movers.append(
            (
                change,
                symbol,
                name,
                coin.get("usd"),
                coin.get("usd_market_cap"),
                coin.get("usd_24h_vol"),
            )
        )

    gainers = sorted(
        movers,
        key=lambda item: item[0],
        reverse=True,
    )[:5]

    losers = sorted(
        movers,
        key=lambda item: item[0],
    )[:5]

    embed = terminal_embed(
        "VEYL / MARKET",
        (
            "```text\n"
            "LIVE MARKET MATRIX\n"
            "────────────────────────────────────────\n"
            f"TIMESTAMP    {timestamp()}\n"
            "SOURCE       MULTI-PROVIDER\n"
            "WINDOW       24H\n"
            f"ASSETS       {len(COINS)}\n"
            "CACHE        ACTIVE\n"
            "STATUS       ONLINE\n"
            "────────────────────────────────────────\n"
            "```"
        ),
    )

    gainers_text = ""

    for index, item in enumerate(
        gainers,
        start=1,
    ):

        change, symbol, _, coin_price, _, _ = item

        gainers_text += (
            f"`{index}` **{symbol:<5}** "
            f"`{price(coin_price):>11}` "
            f"`{change:+.2f}%`\n"
        )

    embed.add_field(
        name="▲ TOP MOVERS",
        value=gainers_text or "No data.",
        inline=True,
    )

    losers_text = ""

    for index, item in enumerate(
        losers,
        start=1,
    ):

        change, symbol, _, coin_price, _, _ = item

        losers_text += (
            f"`{index}` **{symbol:<5}** "
            f"`{price(coin_price):>11}` "
            f"`{change:+.2f}%`\n"
        )

    embed.add_field(
        name="▼ BOTTOM MOVERS",
        value=losers_text or "No data.",
        inline=True,
    )

    matrix = (
        "```text\n"
        "ASSET       PRICE              24H       MKT CAP\n"
        "──────────────────────────────────────────────────\n"
    )

    for coin_id, symbol, _ in COINS[:15]:

        coin = data.get(coin_id)

        if not coin:
            continue

        coin_price = coin.get("usd")

        change = coin.get(
            "usd_24h_change"
        ) or 0

        market_cap = coin.get(
            "usd_market_cap"
        )

        matrix += (
            f"{symbol:<11}"
            f"{price(coin_price):<19}"
            f"{direction(change)} "
            f"{change:+6.2f}%   "
            f"{money(market_cap)}\n"
        )

    matrix += "```"

    embed.add_field(
        name="▤ MARKET MATRIX",
        value=matrix,
        inline=False,
    )

    footer(
        embed,
        "MARKET DATA",
    )

    return embed


# ============================================================
# ASSET VIEW
# ============================================================

def build_asset_view(
    data,
    coin_id,
):

    result = find_coin(coin_id)

    if not result:

        return terminal_embed(
            "VEYL / ASSET",
            "Asset not found.",
        )

    actual_id, symbol, name = result

    coin = data.get(
        actual_id,
        {},
    )

    current = coin.get("usd")
    change = coin.get("usd_24h_change")
    market_cap = coin.get("usd_market_cap")
    volume = coin.get("usd_24h_vol")

    embed = terminal_embed(
        f"VEYL / {symbol}",
        (
            "```text\n"
            "ASSET INTELLIGENCE\n"
            "────────────────────────────────────────\n"
            f"ASSET        {name.upper()}\n"
            f"SYMBOL       {symbol}\n"
            "SOURCE       MULTI-PROVIDER\n"
            "WINDOW       24H\n"
            "CACHE        ACTIVE\n"
            "STATUS       ONLINE\n"
            "────────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="LAST PRICE",
        value=(
            f"**{price(current)}**\n"
            f"`{pct(change)}`  "
            f"{direction(change)}"
        ),
        inline=True,
    )

    embed.add_field(
        name="MARKET CAP",
        value=f"**{money(market_cap)}**",
        inline=True,
    )

    embed.add_field(
        name="24H VOLUME",
        value=f"**{money(volume)}**",
        inline=True,
    )

    embed.add_field(
        name="MARKET STATE",
        value=(
            f"`{direction(change)}`\n"
            "24H CHANGE\n"
            f"`{pct(change)}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="VEYL DATA",
        value=(
            "PRICE       `LIVE`\n"
            "VOLUME      `LIVE`\n"
            "MARKET CAP  `LIVE`\n"
            "CHART       "
            f"`{'READY' if MATPLOTLIB_AVAILABLE else 'OFFLINE'}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="TERMINAL ACTION",
        value=(
            f"Use **CHART** to open "
            f"the 24H {symbol} visualization."
        ),
        inline=True,
    )

    footer(
        embed,
        f"ASSET • {symbol}",
    )

    return embed


# ============================================================
# CHART EMBED
# ============================================================

def build_chart_embed(
    symbol,
    name,
):

    embed = terminal_embed(
        f"VEYL / CHART / {symbol}",
        (
            "```text\n"
            "MARKET CHART ENGINE\n"
            "────────────────────────────────────────\n"
            f"ASSET        {name.upper()}\n"
            f"SYMBOL       {symbol}\n"
            "TIMEFRAME    24H\n"
            "PROVIDER     BINANCE / FALLBACK\n"
            "ENGINE       ONLINE\n"
            "────────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="LIVE MARKET VISUALIZATION",
        value=(
            "Chart generated from live market data.\n\n"
            "`24H`  `USD`  `LIVE CACHE`"
        ),
        inline=False,
    )

    footer(
        embed,
        f"CHART • {symbol}",
    )

    return embed


# ============================================================
# BRAIN
# ============================================================

async def get_brain_analysis():

    try:

        from commands.brain import (
            get_brain_data,
            analyze_market,
        )

        data = await get_brain_data()

        if not data:
            return None

        return analyze_market(data)

    except Exception as error:

        print(
            f"⚠️ Terminal Brain unavailable: {error}"
        )

        return None


async def build_brain_view():

    analysis = await get_brain_analysis()

    if not analysis:

        embed = terminal_embed(
            "VEYL / BRAIN",
            (
                "```text\n"
                "BRAIN ENGINE\n"
                "────────────────────────────────────\n"
                "STATUS       OFFLINE\n"
                "DATA         UNAVAILABLE\n"
                "────────────────────────────────────\n"
                "```\n"
                "The intelligence engine is currently "
                "unavailable."
            ),
        )

        footer(
            embed,
            "BRAIN ENGINE",
        )

        return embed

    score = analysis.get("score", 0)

    if score >= 75:
        regime = "STRONG"
    elif score >= 60:
        regime = "POSITIVE"
    elif score >= 45:
        regime = "NEUTRAL"
    elif score >= 30:
        regime = "WEAK"
    else:
        regime = "CRITICAL"

    state = analysis.get(
        "state",
        "UNKNOWN",
    )

    state_description = analysis.get(
        "state_description",
        "No interpretation available.",
    )

    momentum = analysis.get(
        "momentum",
        0,
    )

    breadth = analysis.get(
        "breadth",
        0,
    )

    volume = analysis.get(
        "volume",
        0,
    )

    volatility = analysis.get(
        "volatility",
        0,
    )

    embed = terminal_embed(
        "VEYL / MARKET BRAIN",
        (
            "```text\n"
            "VEYL INTELLIGENCE\n"
            "BRAIN ENGINE\n"
            "────────────────────────────────────\n"
            "```"
            f"\n**MARKET REGIME**\n"
            f"`{state}`\n"
            f"{state_description}\n\n"
            f"**BRAIN SCORE**\n"
            f"`{score}/100`  `{regime}`"
        ),
    )

    core = (
        f"**MOMENTUM**\n"
        f"`{bar(momentum)}`\n"
        f"`{momentum}/100`\n\n"
        f"**BREADTH**\n"
        f"`{bar(breadth)}`\n"
        f"`{breadth}/100`\n\n"
        f"**VOLUME**\n"
        f"`{bar(volume)}`\n"
        f"`{volume}/100`"
    )

    embed.add_field(
        name="CORE SIGNALS",
        value=core,
        inline=True,
    )

    engine = (
        f"**STABILITY**\n"
        f"`{bar(volatility)}`\n"
        f"`{volatility}/100`\n\n"
        f"**CONFIDENCE**\n"
        f"`{bar(score)}`\n"
        f"`{score}%`\n\n"
        f"**ENGINE**\n"
        f"`ONLINE`"
    )

    embed.add_field(
        name="ENGINE",
        value=engine,
        inline=True,
    )

    embed.add_field(
        name="VEYL INTERPRETATION",
        value=(
            f"`{state}`\n\n"
            f"{state_description}"
        ),
        inline=False,
    )

    footer(
        embed,
        "BRAIN ENGINE",
    )

    return embed


# ============================================================
# STATIC VIEWS
# ============================================================

def build_signals_view():

    embed = terminal_embed(
        "VEYL / SIGNALS",
        (
            "```text\n"
            "SIGNAL ENGINE\n"
            "────────────────────────────────────\n"
            "STATUS       ONLINE\n"
            "BRAIN        CONNECTED\n"
            "FLOW         CONNECTED\n"
            "NEWS         CONNECTED\n"
            "MEMORY       CONNECTED\n"
            "────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="◈ ACTIVE SIGNALS",
        value=(
            "```text\n"
            "NO CONFIRMED SIGNALS\n"
            "MONITORING ACTIVE\n"
            "```\n"
            "No event currently meets the validation "
            "threshold."
        ),
        inline=False,
    )

    embed.add_field(
        name="ENGINE",
        value="`ONLINE`\nBrain + Flow + News",
        inline=True,
    )

    embed.add_field(
        name="CONFIDENCE",
        value="`—`\nAwaiting validated events.",
        inline=True,
    )

    footer(
        embed,
        "SIGNAL ENGINE",
    )

    return embed


def build_anomalies_view():

    embed = terminal_embed(
        "VEYL / ANOMALIES",
        (
            "```text\n"
            "ANOMALY DETECTION ENGINE\n"
            "────────────────────────────────────\n"
            "STATUS       ONLINE\n"
            "PRICE        MONITORING\n"
            "VOLUME       MONITORING\n"
            "WHALES       MONITORING\n"
            "────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="DETECTED ANOMALIES",
        value=(
            "```text\n"
            "NO MAJOR ANOMALY DETECTED\n"
            "MARKET WITHIN NORMAL PARAMETERS\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(
        name="PRICE",
        value="`NORMAL`",
        inline=True,
    )

    embed.add_field(
        name="VOLUME",
        value="`NORMAL`",
        inline=True,
    )

    embed.add_field(
        name="WHALE ACTIVITY",
        value="`NORMAL`",
        inline=True,
    )

    footer(
        embed,
        "ANOMALY ENGINE",
    )

    return embed


def build_flow_view():

    embed = terminal_embed(
        "VEYL / FLOW",
        (
            "```text\n"
            "MARKET FLOW MONITOR\n"
            "────────────────────────────────────\n"
            "LIQUIDITY       MONITORING\n"
            "VOLUME          MONITORING\n"
            "ORDER FLOW      MONITORING\n"
            "EXCHANGE FLOW   MONITORING\n"
            "────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="FLOW STATUS",
        value=(
            "`ONLINE`\n\n"
            "VEYL is preparing flow intelligence "
            "for integration with the terminal."
        ),
        inline=False,
    )

    embed.add_field(
        name="LIQUIDITY",
        value="`MONITORING`",
        inline=True,
    )

    embed.add_field(
        name="VOLUME",
        value="`MONITORING`",
        inline=True,
    )

    embed.add_field(
        name="EXCHANGE FLOW",
        value="`STANDBY`",
        inline=True,
    )

    footer(
        embed,
        "FLOW ENGINE",
    )

    return embed


def build_news_view():

    embed = terminal_embed(
        "VEYL / NEWS",
        (
            "```text\n"
            "MARKET INTELLIGENCE NEWS\n"
            "────────────────────────────────────\n"
            "SOURCE ENGINE     ONLINE\n"
            "EVENT MONITOR     ONLINE\n"
            "SENTIMENT         STANDBY\n"
            "────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="NEWS FEED",
        value=(
            "```text\n"
            "NO LIVE HEADLINES LOADED\n"
            "NEWS ENGINE READY\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(
        name="STATUS",
        value="`ONLINE`",
        inline=True,
    )

    embed.add_field(
        name="SENTIMENT",
        value="`STANDBY`",
        inline=True,
    )

    embed.add_field(
        name="EVENTS",
        value="`MONITORING`",
        inline=True,
    )

    footer(
        embed,
        "NEWS ENGINE",
    )

    return embed


def build_system_view(bot):

    embed = terminal_embed(
        "VEYL / SYSTEM",
        (
            "```text\n"
            "VEYL TERMINAL SYSTEM\n"
            "────────────────────────────────────\n"
            "CORE             ONLINE\n"
            "DISCORD          ONLINE\n"
            "MARKET ENGINE    ONLINE\n"
            "CHART ENGINE     "
            f"{'ONLINE' if MATPLOTLIB_AVAILABLE else 'OFFLINE'}\n"
            "CACHE LAYER      ONLINE\n"
            "NAVIGATION       ONLINE\n"
            "────────────────────────────────────\n"
            "```"
        ),
    )

    embed.add_field(
        name="BOT",
        value=(
            f"USER       `{bot.user}`\n"
            f"SERVERS    `{len(bot.guilds)}`\n"
            f"COMMANDS   `{len(bot.tree.get_commands())}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="TERMINAL",
        value=(
            "VERSION    `10.1`\n"
            "MODE       `INSTITUTIONAL`\n"
            "STATUS     `ONLINE`"
        ),
        inline=True,
    )

    embed.add_field(
        name="DATA",
        value=(
            "SOURCE     `MULTI-PROVIDER`\n"
            f"ASSETS     `{len(COINS)}`\n"
            "CACHE      `ACTIVE`\n"
            "WINDOW     `24H`"
        ),
        inline=True,
    )

    footer(
        embed,
        "SYSTEM",
    )

    return embed


# ============================================================
# ASSET SELECT
# ============================================================

class AssetSelect(discord.ui.Select):

    def __init__(self):

        options = []

        for coin_id, symbol, name in COINS:

            options.append(
                discord.SelectOption(
                    label=f"{symbol} — {name}",
                    value=coin_id,
                    description=f"Open {symbol} intelligence",
                )
            )

        super().__init__(
            placeholder="SELECT ASSET",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="veyl_terminal_asset_select",
            row=3,
        )

    async def callback(self, interaction):

        await interaction.response.defer()

        coin_id = self.values[0]

        data = await get_market_data()

        if not data:

            await interaction.followup.send(
                "VEYL market data is temporarily unavailable.",
                ephemeral=True,
            )

            return

        embed = build_asset_view(
            data,
            coin_id,
        )

        await interaction.message.edit(
            embed=embed,
            view=self.view,
            attachments=[],
        )


# ============================================================
# TERMINAL VIEW
# ============================================================

class TerminalView(discord.ui.View):

    def __init__(self, bot):

        super().__init__(
            timeout=None
        )

        self.bot = bot
        self.last_refresh = 0

        self.add_item(
            AssetSelect()
        )

    # ========================================================
    # HOME
    # ========================================================

    @discord.ui.button(
        label="HOME",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_home",
        row=0,
    )
    async def home(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        try:
            data = await get_market_data()
        except Exception as error:
            print(f"⚠️ Terminal HOME error: {error}")
            data = None

        embed = (
            build_cockpit(data)
            if data
            else build_offline_cockpit()
        )

        await interaction.message.edit(
            embed=embed,
            view=self,
            attachments=[],
        )

    # ========================================================
    # MARKET
    # ========================================================

    @discord.ui.button(
        label="MARKET",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_market",
        row=0,
    )
    async def market(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        try:
            data = await get_market_data()
        except Exception as error:
            print(f"⚠️ Terminal MARKET error: {error}")
            data = None

        if not data:

            await interaction.followup.send(
                "Market data temporarily unavailable.",
                ephemeral=True,
            )

            return

        await interaction.message.edit(
            embed=build_market_view(data),
            view=self,
            attachments=[],
        )

    # ========================================================
    # CHART
    # ========================================================

    @discord.ui.button(
        label="CHART",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_chart",
        row=0,
    )
    async def chart(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        if not MATPLOTLIB_AVAILABLE:

            await interaction.followup.send(
                "Chart engine offline: matplotlib is not installed.",
                ephemeral=True,
            )

            return

        result = find_coin("SOL")

        if not result:

            await interaction.followup.send(
                "Default chart asset unavailable.",
                ephemeral=True,
            )

            return

        coin_id, symbol, name = result

        print(
            f"⌘ VEYL Chart → requesting {symbol} / 24H"
        )

        try:

            chart_file = await create_chart(
                coin_id=coin_id,
                symbol=symbol,
                name=name,
                days=1,
            )

        except Exception as error:

            print(
                f"❌ VEYL Chart error: {error}"
            )

            await interaction.followup.send(
                "VEYL Chart Engine encountered an error.",
                ephemeral=True,
            )

            return

        if not chart_file:

            await interaction.followup.send(
                (
                    "VEYL could not generate the chart.\n"
                    "The chart provider may be temporarily "
                    "unavailable or rate-limited."
                ),
                ephemeral=True,
            )

            return

        embed = build_chart_embed(
            symbol,
            name,
        )

        embed.set_image(
            url="attachment://veyl_chart.png"
        )

        file = discord.File(
            chart_file,
            filename="veyl_chart.png",
        )

        await interaction.message.edit(
            embed=embed,
            view=self,
            attachments=[file],
        )

        print(
            f"✅ VEYL Chart displayed → {symbol}"
        )

    # ========================================================
    # BRAIN
    # ========================================================

    @discord.ui.button(
        label="BRAIN",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_brain",
        row=0,
    )
    async def brain(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        embed = await build_brain_view()

        await interaction.message.edit(
            embed=embed,
            view=self,
            attachments=[],
        )

    # ========================================================
    # SIGNALS
    # ========================================================

    @discord.ui.button(
        label="SIGNALS",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_signals",
        row=0,
    )
    async def signals(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        await interaction.message.edit(
            embed=build_signals_view(),
            view=self,
            attachments=[],
        )

    # ========================================================
    # ANOMALIES
    # ========================================================

    @discord.ui.button(
        label="ANOMALIES",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_anomalies",
        row=1,
    )
    async def anomalies(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        await interaction.message.edit(
            embed=build_anomalies_view(),
            view=self,
            attachments=[],
        )

    # ========================================================
    # FLOW
    # ========================================================

    @discord.ui.button(
        label="FLOW",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_flow",
        row=1,
    )
    async def flow(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        await interaction.message.edit(
            embed=build_flow_view(),
            view=self,
            attachments=[],
        )

    # ========================================================
    # NEWS
    # ========================================================

    @discord.ui.button(
        label="NEWS",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_news",
        row=1,
    )
    async def news(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        await interaction.message.edit(
            embed=build_news_view(),
            view=self,
            attachments=[],
        )

    # ========================================================
    # SYSTEM
    # ========================================================

    @discord.ui.button(
        label="SYSTEM",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_system",
        row=1,
    )
    async def system(
        self,
        interaction,
        button,
    ):

        await interaction.response.defer()

        await interaction.message.edit(
            embed=build_system_view(
                self.bot
            ),
            view=self,
            attachments=[],
        )

    # ========================================================
    # REFRESH
    # ========================================================

    @discord.ui.button(
        label="REFRESH",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_terminal_refresh",
        row=2,
    )
    async def refresh(
        self,
        interaction,
        button,
    ):

        current_time = time.monotonic()

        elapsed = (
            current_time
            - self.last_refresh
        )

        if elapsed < REFRESH_COOLDOWN:

            remaining = (
                int(
                    REFRESH_COOLDOWN
                    - elapsed
                )
                + 1
            )

            await interaction.response.send_message(
                (
                    "Refresh available in "
                    f"`{remaining}s`."
                ),
                ephemeral=True,
            )

            return

        self.last_refresh = current_time

        await interaction.response.defer()

        try:
            data = await get_market_data(
                force=True
            )
        except Exception as error:
            print(
                f"⚠️ Terminal REFRESH error: {error}"
            )
            data = None

        embed = (
            build_cockpit(data)
            if data
            else build_offline_cockpit()
        )

        await interaction.message.edit(
            embed=embed,
            view=self,
            attachments=[],
        )


# ============================================================
# COG
# ============================================================

class VeylTerminal(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        print(
            "⌘ VEYL Terminal 10.1 activated."
        )

    async def cog_load(self):

        self.bot.add_view(
            TerminalView(
                self.bot
            )
        )

        print(
            "   ✓ Persistent terminal view"
        )

    # ========================================================
    # /TERMINAL
    # ========================================================

    @app_commands.command(
        name="terminal",
        description="Open the VEYL Terminal 10.1.",
    )
    async def terminal(
        self,
        interaction: discord.Interaction,
    ):

        channel = interaction.channel

        if (
            channel is None
            or channel.name != TERMINAL_CHANNEL
        ):

            await interaction.response.send_message(
                (
                    "Please use `/terminal` in "
                    f"`{TERMINAL_CHANNEL}`."
                ),
                ephemeral=True,
            )

            return

        # ----------------------------------------------------
        # IMPORTANT
        # ----------------------------------------------------
        # We open the interface FIRST.
        # Market data cannot prevent the Terminal from opening.
        # ----------------------------------------------------

        await interaction.response.defer()

        try:

            data = await get_market_data()

        except Exception as error:

            print(
                f"⚠️ VEYL Terminal market error: {error}"
            )

            data = None

        if data:

            embed = build_cockpit(data)

        else:

            embed = build_offline_cockpit()

        view = TerminalView(
            self.bot
        )

        view.last_refresh = time.monotonic()

        try:

            await interaction.followup.send(
                embed=embed,
                view=view,
            )

        except Exception as error:

            print(
                f"❌ VEYL Terminal interface error: {error}"
            )

            await interaction.followup.send(
                (
                    "VEYL Terminal failed while sending "
                    "the interface."
                ),
                ephemeral=True,
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylTerminal(bot)
    )

    print(
        "   ✓ commands.terminal"
    )