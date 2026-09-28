import time
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from services.market import (
    get_crypto_price_async,
)


# ============================================================
# VEYL BRAIN — PHASE 4
# MARKET INTELLIGENCE ENGINE
# ============================================================

CHECK_INTERVAL = 60
REFRESH_COOLDOWN = 20


# ============================================================
# MARKET UNIVERSE
# ============================================================

BRAIN_COINS = [
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
# INTERNAL STATE
# ============================================================

_previous_analysis = None


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


def bar(
    score,
    length=14,
):

    score = clamp(score)

    filled = round(
        (score / 100) * length
    )

    return (
        "█" * filled
        + "░" * (length - filled)
    )


def direction_icon(value):

    if value > 0:
        return "🟢"

    if value < 0:
        return "🔴"

    return "⚪"


def score_status(score):

    if score >= 80:
        return "VERY STRONG"

    if score >= 65:
        return "STRONG"

    if score >= 55:
        return "POSITIVE"

    if score >= 45:
        return "NEUTRAL"

    if score >= 35:
        return "WEAK"

    return "CRITICAL"


# ============================================================
# MARKET DATA
# ============================================================

async def get_brain_data():

    data = {}

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Brain utilise maintenant le service market.py.
    # Cela permet de profiter de son cache + backoff.
    # --------------------------------------------------------

    async def fetch_coin(
        coin_id,
    ):

        try:

            result = await get_crypto_price_async(
                coin_id
            )

            return (
                coin_id,
                result,
            )

        except Exception as error:

            print(
                f"⚠️ Brain coin error "
                f"{coin_id}: {error}"
            )

            return (
                coin_id,
                None,
            )

    results = await asyncio.gather(
        *[
            fetch_coin(coin_id)
            for coin_id, _ in BRAIN_COINS
        ],
        return_exceptions=False,
    )

    for coin_id, coin_data in results:

        if coin_data:

            data[coin_id] = coin_data

    if not data:

        return None

    return data


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(data):

    changes = []

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is not None:
            changes.append(
                change
            )

    if not changes:
        return 50

    average = (
        sum(changes)
        / len(changes)
    )

    score = 50 + (
        average * 5
    )

    return round(
        clamp(score)
    )


# ============================================================
# BREADTH
# ============================================================

def calculate_breadth(data):

    positive = 0
    negative = 0
    unchanged = 0

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

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
            unchanged += 1

    total = (
        positive
        + negative
        + unchanged
    )

    if total == 0:
        return 50

    score = (
        positive / total
    ) * 100

    return round(
        clamp(score)
    )


# ============================================================
# VOLUME PARTICIPATION
# ============================================================

def calculate_volume(data):

    volumes = []

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        volume = coin.get(
            "usd_24h_vol"
        )

        if volume:
            volumes.append(
                volume
            )

    if not volumes:
        return 50

    total_volume = sum(
        volumes
    )

    if total_volume <= 0:
        return 50

    largest = max(
        volumes
    )

    concentration = (
        largest
        / total_volume
    )

    participation = (
        100
        - concentration * 100
    )

    score = 50 + (
        participation - 50
    ) * 1.5

    return round(
        clamp(score)
    )


# ============================================================
# VOLATILITY / STABILITY
# ============================================================

def calculate_volatility(data):

    changes = []

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is not None:

            changes.append(
                abs(change)
            )

    if not changes:
        return 50

    average = (
        sum(changes)
        / len(changes)
    )

    score = 100 - (
        average * 8
    )

    return round(
        clamp(score)
    )


# ============================================================
# BULL PRESSURE
# ============================================================

def calculate_bull_pressure(
    data,
):

    positive_weight = 0
    total_weight = 0

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        volume = coin.get(
            "usd_24h_vol"
        )

        if change is None:
            continue

        weight = (
            volume
            if volume
            else 1
        )

        total_weight += weight

        if change > 0:

            strength = clamp(
                50 + change * 5
            ) / 100

            positive_weight += (
                weight * strength
            )

    if total_weight <= 0:
        return 50

    score = (
        positive_weight
        / total_weight
    ) * 100

    return round(
        clamp(score)
    )


# ============================================================
# BEAR PRESSURE
# ============================================================

def calculate_bear_pressure(
    data,
):

    negative_weight = 0
    total_weight = 0

    for coin_id, _ in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        volume = coin.get(
            "usd_24h_vol"
        )

        if change is None:
            continue

        weight = (
            volume
            if volume
            else 1
        )

        total_weight += weight

        if change < 0:

            strength = clamp(
                50 + abs(change) * 5
            ) / 100

            negative_weight += (
                weight * strength
            )

    if total_weight <= 0:
        return 50

    score = (
        negative_weight
        / total_weight
    ) * 100

    return round(
        clamp(score)
    )


# ============================================================
# MARKET STRESS
# ============================================================

def calculate_market_stress(
    breadth,
    volatility,
    momentum,
):

    breadth_stress = (
        100 - breadth
    )

    volatility_stress = (
        100 - volatility
    )

    momentum_stress = (
        100 - momentum
    )

    score = (
        breadth_stress * 0.45
        + volatility_stress * 0.30
        + momentum_stress * 0.25
    )

    return round(
        clamp(score)
    )


# ============================================================
# MARKET CONVICTION
# ============================================================

def calculate_conviction(
    bull_pressure,
    bear_pressure,
    breadth,
    momentum,
):

    pressure_difference = abs(
        bull_pressure
        - bear_pressure
    )

    directional_strength = (
        pressure_difference
        * 0.45
    )

    breadth_strength = abs(
        breadth - 50
    ) * 0.25

    momentum_strength = abs(
        momentum - 50
    ) * 0.30

    conviction = (
        directional_strength
        + breadth_strength
        + momentum_strength
    )

    return round(
        clamp(conviction)
    )


# ============================================================
# REGIME
# ============================================================

def determine_regime(
    score,
    momentum,
    breadth,
    volume,
    volatility,
    bull_pressure,
    bear_pressure,
):

    # --------------------------------------------------------
    # EXPANSION
    # --------------------------------------------------------

    if (
        score >= 72
        and momentum >= 68
        and breadth >= 62
        and bull_pressure > bear_pressure
    ):

        return (
            "EXPANSION",
            "🟢",
            "Broad market strength is accelerating.",
        )

    # --------------------------------------------------------
    # ACCUMULATION
    # --------------------------------------------------------

    if (
        score >= 58
        and momentum >= 52
        and breadth >= 52
        and bull_pressure >= bear_pressure
    ):

        return (
            "ACCUMULATION",
            "🔵",
            "Positive participation is building.",
        )

    # --------------------------------------------------------
    # ROTATION
    # --------------------------------------------------------

    if (
        momentum >= 55
        and breadth < 52
        and volume >= 45
    ):

        return (
            "ROTATION",
            "🟡",
            "Strength is concentrated in selected assets.",
        )

    # --------------------------------------------------------
    # DISTRIBUTION
    # --------------------------------------------------------

    if (
        score < 46
        and breadth < 46
        and bear_pressure > bull_pressure
    ):

        return (
            "DISTRIBUTION",
            "🟠",
            "Selling pressure is spreading across the market.",
        )

    # --------------------------------------------------------
    # CAPITULATION
    # --------------------------------------------------------

    if (
        score < 30
        and momentum < 30
        and breadth < 30
        and bear_pressure > 65
    ):

        return (
            "CAPITULATION",
            "🔴",
            "Severe broad-market weakness detected.",
        )

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    if (
        momentum >= 55
        and breadth < 50
        and score >= 50
    ):

        return (
            "RECOVERY",
            "🟣",
            "Momentum is recovering before broad participation.",
        )

    return (
        "NEUTRAL",
        "⚪",
        "No dominant market regime detected.",
    )


# ============================================================
# MOMENTUM SHIFT
# ============================================================

def calculate_momentum_shift(
    current_score,
):

    global _previous_analysis

    if not _previous_analysis:

        return {
            "value": 0,
            "label": "INITIALIZING",
            "emoji": "⚪",
        }

    previous = _previous_analysis.get(
        "score",
        current_score,
    )

    difference = (
        current_score
        - previous
    )

    if difference >= 8:

        return {
            "value": difference,
            "label": "ACCELERATING",
            "emoji": "🟢",
        }

    if difference >= 3:

        return {
            "value": difference,
            "label": "IMPROVING",
            "emoji": "🔵",
        }

    if difference <= -8:

        return {
            "value": difference,
            "label": "REVERSING",
            "emoji": "🔴",
        }

    if difference <= -3:

        return {
            "value": difference,
            "label": "WEAKENING",
            "emoji": "🟠",
        }

    return {
        "value": difference,
        "label": "STABLE",
        "emoji": "⚪",
    }


# ============================================================
# REGIME CHANGE
# ============================================================

def detect_regime_change(
    current_regime,
):

    global _previous_analysis

    if not _previous_analysis:

        return {
            "changed": False,
            "text": "Initial market regime established.",
        }

    previous_regime = (
        _previous_analysis.get(
            "state"
        )
    )

    if (
        previous_regime
        and previous_regime != current_regime
    ):

        return {
            "changed": True,
            "text": (
                f"Regime shifted from "
                f"{previous_regime} → "
                f"{current_regime}"
            ),
        }

    return {
        "changed": False,
        "text": (
            f"Regime remains "
            f"{current_regime}."
        ),
    }


# ============================================================
# INTERPRETATION ENGINE
# ============================================================

def generate_interpretation(
    analysis,
):

    score = analysis["score"]
    momentum = analysis["momentum"]
    breadth = analysis["breadth"]
    bull = analysis["bull_pressure"]
    bear = analysis["bear_pressure"]
    stress = analysis["market_stress"]
    shift = analysis["momentum_shift"]

    messages = []

    # --------------------------------------------------------
    # DOMINANT PRESSURE
    # --------------------------------------------------------

    if bull > bear + 15:

        messages.append(
            "Buy-side pressure is currently dominant."
        )

    elif bear > bull + 15:

        messages.append(
            "Sell-side pressure is currently dominant."
        )

    else:

        messages.append(
            "Market pressure remains relatively balanced."
        )

    # --------------------------------------------------------
    # BREADTH
    # --------------------------------------------------------

    if breadth >= 70:

        messages.append(
            "Participation is broad across tracked assets."
        )

    elif breadth <= 30:

        messages.append(
            "Market participation is unusually weak."
        )

    else:

        messages.append(
            "Participation remains mixed."
        )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if momentum >= 70:

        messages.append(
            "Momentum is strong."
        )

    elif momentum <= 30:

        messages.append(
            "Momentum is significantly weakened."
        )

    # --------------------------------------------------------
    # STRESS
    # --------------------------------------------------------

    if stress >= 70:

        messages.append(
            "Market stress is elevated."
        )

    elif stress <= 30:

        messages.append(
            "Market conditions remain relatively calm."
        )

    # --------------------------------------------------------
    # SHIFT
    # --------------------------------------------------------

    if shift["label"] == "ACCELERATING":

        messages.append(
            "The Brain score is accelerating versus the previous reading."
        )

    elif shift["label"] == "REVERSING":

        messages.append(
            "The Brain score is reversing versus the previous reading."
        )

    return " ".join(
        messages
    )


# ============================================================
# ANALYSIS
# ============================================================

def analyze_market(
    data,
):

    global _previous_analysis

    momentum = calculate_momentum(
        data
    )

    breadth = calculate_breadth(
        data
    )

    volume = calculate_volume(
        data
    )

    volatility = calculate_volatility(
        data
    )

    bull_pressure = calculate_bull_pressure(
        data
    )

    bear_pressure = calculate_bear_pressure(
        data
    )

    market_stress = calculate_market_stress(
        breadth,
        volatility,
        momentum,
    )

    # --------------------------------------------------------
    # BRAIN SCORE
    # --------------------------------------------------------

    brain_score = (
        momentum * 0.28
        + volume * 0.17
        + breadth * 0.25
        + volatility * 0.10
        + bull_pressure * 0.20
    )

    # Bear pressure penalizes the global score.

    if bear_pressure > bull_pressure:

        penalty = (
            bear_pressure
            - bull_pressure
        ) * 0.15

        brain_score -= penalty

    brain_score = round(
        clamp(
            brain_score
        )
    )

    # --------------------------------------------------------
    # REGIME
    # --------------------------------------------------------

    state, state_emoji, state_description = determine_regime(
        brain_score,
        momentum,
        breadth,
        volume,
        volatility,
        bull_pressure,
        bear_pressure,
    )

    # --------------------------------------------------------
    # MOMENTUM SHIFT
    # --------------------------------------------------------

    momentum_shift = calculate_momentum_shift(
        brain_score
    )

    # --------------------------------------------------------
    # REGIME CHANGE
    # --------------------------------------------------------

    regime_change = detect_regime_change(
        state
    )

    # --------------------------------------------------------
    # CONVICTION
    # --------------------------------------------------------

    conviction = calculate_conviction(
        bull_pressure,
        bear_pressure,
        breadth,
        momentum,
    )

    analysis = {

        "score": brain_score,

        "momentum": momentum,

        "volume": volume,

        "breadth": breadth,

        "volatility": volatility,

        "bull_pressure": bull_pressure,

        "bear_pressure": bear_pressure,

        "market_stress": market_stress,

        "conviction": conviction,

        "state": state,

        "state_emoji": state_emoji,

        "state_description": state_description,

        "momentum_shift": momentum_shift,

        "regime_change": regime_change,

    }

    analysis["interpretation"] = generate_interpretation(
        analysis
    )

    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    _previous_analysis = analysis.copy()

    return analysis


# ============================================================
# LEADERS
# ============================================================

def get_leaders(
    data,
):

    leaders = []

    for coin_id, symbol in BRAIN_COINS:

        coin = data.get(
            coin_id
        )

        if not coin:
            continue

        pct = coin.get(
            "usd_24h_change"
        )

        price = coin.get(
            "usd"
        )

        if pct is None:
            continue

        leaders.append(
            (
                pct,
                symbol,
                price,
            )
        )

    return sorted(
        leaders,
        key=lambda x: x[0],
        reverse=True,
    )


# ============================================================
# EMBED
# ============================================================

def build_brain_embed(
    data,
    analysis,
):

    now = time.strftime(
        "%H:%M:%S"
    )

    score = analysis["score"]

    status = score_status(
        score
    )

    # --------------------------------------------------------
    # MAIN EMBED
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🧠  VEYL // MARKET BRAIN",
        description=(
            "```text\n"
            "╔══════════════════════════════════════════════╗\n"
            "║              VEYL MARKET BRAIN              ║\n"
            "║         INTELLIGENCE ENGINE • PHASE 4       ║\n"
            "╚══════════════════════════════════════════════╝\n"
            "```\n"
            f"**MARKET REGIME**  "
            f"{analysis['state_emoji']} "
            f"**{analysis['state']}**\n"
            f"{analysis['state_description']}\n\n"
            f"**BRAIN SCORE**  "
            f"`{score}/100`  "
            f"**{status}**"
        ),
        color=discord.Color.blurple(),
    )

    # ========================================================
    # CORE SIGNALS
    # ========================================================

    core = (
        f"**MOMENTUM**\n"
        f"`{bar(analysis['momentum'])}` "
        f"**{analysis['momentum']}**\n\n"

        f"**BREADTH**\n"
        f"`{bar(analysis['breadth'])}` "
        f"**{analysis['breadth']}**\n\n"

        f"**VOLUME**\n"
        f"`{bar(analysis['volume'])}` "
        f"**{analysis['volume']}**"
    )

    embed.add_field(
        name="◈ CORE SIGNALS",
        value=core,
        inline=True,
    )

    # ========================================================
    # PRESSURE
    # ========================================================

    pressure = (
        f"🟢 **BULL PRESSURE**\n"
        f"`{bar(analysis['bull_pressure'])}` "
        f"**{analysis['bull_pressure']}**\n\n"

        f"🔴 **BEAR PRESSURE**\n"
        f"`{bar(analysis['bear_pressure'])}` "
        f"**{analysis['bear_pressure']}**\n\n"

        f"⚖️ **CONVICTION**\n"
        f"`{bar(analysis['conviction'])}` "
        f"**{analysis['conviction']}**"
    )

    embed.add_field(
        name="⚔ MARKET PRESSURE",
        value=pressure,
        inline=True,
    )

    # ========================================================
    # ENGINE
    # ========================================================

    engine = (
        f"**STABILITY**\n"
        f"`{bar(analysis['volatility'])}` "
        f"**{analysis['volatility']}**\n\n"

        f"**MARKET STRESS**\n"
        f"`{bar(analysis['market_stress'])}` "
        f"**{analysis['market_stress']}**\n\n"

        f"**CONFIDENCE**\n"
        f"`{bar(analysis['conviction'])}` "
        f"**{analysis['conviction']}%**"
    )

    embed.add_field(
        name="⚡ ENGINE",
        value=engine,
        inline=True,
    )

    # ========================================================
    # MOMENTUM SHIFT
    # ========================================================

    shift = analysis[
        "momentum_shift"
    ]

    shift_text = (
        f"{shift['emoji']} "
        f"**{shift['label']}**\n\n"
        f"Change: "
        f"`{shift['value']:+d}` points\n\n"
        f"Previous Brain reading comparison."
    )

    embed.add_field(
        name="⚡ MOMENTUM SHIFT",
        value=shift_text,
        inline=True,
    )

    # ========================================================
    # REGIME CHANGE
    # ========================================================

    regime_change = analysis[
        "regime_change"
    ]

    if regime_change["changed"]:

        regime_text = (
            "🚨 **REGIME CHANGE DETECTED**\n\n"
            f"{regime_change['text']}"
        )

    else:

        regime_text = (
            "🟢 **REGIME STABLE**\n\n"
            f"{regime_change['text']}"
        )

    embed.add_field(
        name="🔄 REGIME MONITOR",
        value=regime_text,
        inline=True,
    )

    # ========================================================
    # LEADERS
    # ========================================================

    leaders = get_leaders(
        data
    )

    leaders_text = ""

    for index, (
        pct,
        symbol,
        coin_price,
    ) in enumerate(
        leaders[:5],
        start=1,
    ):

        leaders_text += (
            f"`{index}` "
            f"**{symbol:<5}** "
            f"`{format_price(coin_price):>12}` "
            f"{direction_icon(pct)} "
            f"**{pct:+.2f}%**\n"
        )

    embed.add_field(
        name="📈 MOMENTUM LEADERS",
        value=(
            leaders_text
            or "No market data."
        ),
        inline=True,
    )

    # ========================================================
    # CORE ASSETS
    # ========================================================

    core_assets = ""

    for coin_id, symbol in [
        ("bitcoin", "BTC"),
        ("ethereum", "ETH"),
        ("solana", "SOL"),
    ]:

        coin = data.get(
            coin_id,
            {},
        )

        coin_price = coin.get(
            "usd"
        )

        pct = coin.get(
            "usd_24h_change"
        )

        if pct is None:
            pct = 0

        core_assets += (
            f"{direction_icon(pct)} "
            f"**{symbol}**  "
            f"`{format_price(coin_price)}`  "
            f"`{pct:+.2f}%`\n"
        )

    embed.add_field(
        name="▣ CORE ASSETS",
        value=core_assets,
        inline=True,
    )

    # ========================================================
    # INTERPRETATION
    # ========================================================

    interpretation = (
        f"**VEYL READ**\n"
        f"{analysis['interpretation']}\n\n"
        f"Updated `{now}`"
    )

    embed.add_field(
        name="🧠 INTELLIGENCE",
        value=interpretation,
        inline=False,
    )

    # ========================================================
    # FOOTER
    # ========================================================

    embed.set_footer(
        text=(
            "VEYL • MARKET BRAIN • PHASE 4 "
            "• Market Intelligence Engine"
        )
    )

    return embed


# ============================================================
# BRAIN VIEW
# ============================================================

class BrainView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.last_refresh = 0

    @discord.ui.button(
        label="Refresh Brain",
        style=discord.ButtonStyle.secondary,
        custom_id="veyl_brain_refresh",
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        current_time = time.time()

        if (
            current_time
            - self.last_refresh
            < REFRESH_COOLDOWN
        ):

            remaining = int(
                REFRESH_COOLDOWN
                - (
                    current_time
                    - self.last_refresh
                )
            ) + 1

            await interaction.response.send_message(
                f"⏳ Brain refresh available "
                f"in **{remaining}s**.",
                ephemeral=True,
            )

            return

        self.last_refresh = (
            current_time
        )

        await interaction.response.defer()

        data = await get_brain_data()

        if data is None:

            await interaction.followup.send(
                "⚠️ VEYL Brain could not retrieve "
                "market data.",
                ephemeral=True,
            )

            return

        analysis = analyze_market(
            data
        )

        embed = build_brain_embed(
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
                f"⚠️ VEYL Brain Discord error : "
                f"{error}"
            )


# ============================================================
# COG
# ============================================================

class VeylBrain(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):

        self.bot = bot

        print(
            "🧠 VEYL Brain Phase 4 activé."
        )

    # ========================================================
    # /BRAIN
    # ========================================================

    @app_commands.command(
        name="brain",
        description=(
            "Analyze the crypto market with VEYL Brain."
        ),
    )
    async def brain(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.defer()

        data = await get_brain_data()

        if data is None:

            await interaction.followup.send(
                "⚠️ VEYL Brain could not retrieve "
                "market data right now.",
                ephemeral=True,
            )

            return

        analysis = analyze_market(
            data
        )

        embed = build_brain_embed(
            data,
            analysis,
        )

        view = BrainView()

        view.last_refresh = (
            time.time()
        )

        await interaction.followup.send(
            embed=embed,
            view=view,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot,
):

    await bot.add_cog(
        VeylBrain(bot)
    )

    print(
        "   ✅ commands.brain"
    )