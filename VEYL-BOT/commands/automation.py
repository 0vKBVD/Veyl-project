import asyncio
import json
import os
import time
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks


# ============================================================
# VEYL AUTOMATION ENGINE
# PHASE 6 — AUTONOMOUS MARKET MONITOR
# ============================================================

AUTOMATION_CHANNEL = "bot-🤖"

REQUEST_TIMEOUT = 10
CHECK_INTERVAL = 60

# Minimum variation between two scans before VEYL considers
# a movement interesting.
PRICE_ALERT_THRESHOLD = 3.0

# Volume multiplier required for an abnormal volume event.
VOLUME_ANOMALY_MULTIPLIER = 2.0

# Prevent the same alert from being spammed.
ALERT_COOLDOWN = 15 * 60

# Memory file
MEMORY_FILE = "veyl_automation_memory.json"


# ============================================================
# MARKET
# ============================================================

COINS = [
    ("bitcoin", "BTC"),
    ("ethereum", "ETH"),
    ("tether", "USDT"),
    ("binancecoin", "BNB"),
    ("solana", "SOL"),
    ("usd-coin", "USDC"),
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


COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
)


# ============================================================
# FORMAT
# ============================================================

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


def format_percent(value):

    if value is None:
        return "—"

    return f"{value:+.2f}%"


# ============================================================
# MEMORY
# ============================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {
            "snapshots": {},
            "alerts": {},
        }

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid memory format.")

            data.setdefault("snapshots", {})
            data.setdefault("alerts", {})

            return data

    except Exception as error:

        print(
            f"⚠️ VEYL Automation memory reset : {error}"
        )

        return {
            "snapshots": {},
            "alerts": {},
        }


def save_memory(memory):

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                memory,
                file,
                indent=2,
            )

    except Exception as error:

        print(
            f"⚠️ VEYL Automation memory error : {error}"
        )


# ============================================================
# API
# ============================================================

async def get_market_data():

    ids = ",".join(
        coin_id
        for coin_id, _ in COINS
    )

    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
    }

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    headers = {
        "User-Agent": "VEYL-Automation/6.0"
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
                        "⚠️ VEYL Automation : CoinGecko HTTP 429."
                    )

                    return None

                if response.status != 200:

                    print(
                        f"⚠️ VEYL Automation : CoinGecko "
                        f"HTTP {response.status}."
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        print(
            "⚠️ VEYL Automation : API timeout."
        )

        return None

    except aiohttp.ClientError as error:

        print(
            f"⚠️ VEYL Automation network error : {error}"
        )

        return None

    except Exception as error:

        print(
            f"❌ VEYL Automation API error : {error}"
        )

        return None


# ============================================================
# CHANNEL
# ============================================================

def find_automation_channel(bot):

    for guild in bot.guilds:

        for channel in guild.text_channels:

            if channel.name == AUTOMATION_CHANNEL:
                return channel

    return None


# ============================================================
# ALERT COOLDOWN
# ============================================================

def alert_allowed(memory, alert_key):

    now = time.time()

    last_alert = memory["alerts"].get(
        alert_key,
        0,
    )

    if now - last_alert < ALERT_COOLDOWN:
        return False

    memory["alerts"][alert_key] = now

    return True


# ============================================================
# PRICE ANOMALY
# ============================================================

def detect_price_anomalies(
    data,
    memory,
):

    events = []

    snapshots = memory["snapshots"]

    for coin_id, symbol in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        current_price = coin.get("usd")

        if current_price is None:
            continue

        previous = snapshots.get(symbol)

        if not previous:
            continue

        previous_price = previous.get("price")

        if not previous_price:
            continue

        movement = (
            (current_price - previous_price)
            / previous_price
        ) * 100

        if abs(movement) < PRICE_ALERT_THRESHOLD:
            continue

        direction = (
            "UP"
            if movement > 0
            else "DOWN"
        )

        alert_key = (
            f"price:{symbol}:{direction}"
        )

        if not alert_allowed(
            memory,
            alert_key,
        ):
            continue

        events.append(
            {
                "type": "PRICE_ANOMALY",
                "symbol": symbol,
                "price": current_price,
                "movement": movement,
                "direction": direction,
            }
        )

    return events


# ============================================================
# VOLUME ANOMALY
# ============================================================

def detect_volume_anomalies(
    data,
    memory,
):

    events = []

    snapshots = memory["snapshots"]

    for coin_id, symbol in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        volume = coin.get(
            "usd_24h_vol"
        )

        if not volume:
            continue

        previous = snapshots.get(symbol)

        if not previous:
            continue

        previous_volume = previous.get(
            "volume"
        )

        if not previous_volume:
            continue

        ratio = (
            volume
            / previous_volume
        )

        if ratio < VOLUME_ANOMALY_MULTIPLIER:
            continue

        alert_key = (
            f"volume:{symbol}"
        )

        if not alert_allowed(
            memory,
            alert_key,
        ):
            continue

        events.append(
            {
                "type": "VOLUME_ANOMALY",
                "symbol": symbol,
                "volume": volume,
                "previous_volume": previous_volume,
                "ratio": ratio,
            }
        )

    return events


# ============================================================
# MARKET EVENT
# ============================================================

def detect_market_event(data):

    positive = 0
    negative = 0
    neutral = 0

    changes = []

    for coin_id, symbol in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        change = coin.get(
            "usd_24h_change"
        )

        if change is None:
            continue

        changes.append(change)

        if change > 1:
            positive += 1

        elif change < -1:
            negative += 1

        else:
            neutral += 1

    if not changes:
        return None

    breadth = (
        positive / len(changes)
    ) * 100

    average = sum(changes) / len(changes)

    if breadth >= 70 and average >= 2:

        return {
            "type": "MARKET_BULLISH",
            "breadth": breadth,
            "average": average,
            "positive": positive,
            "negative": negative,
        }

    if (
        negative / len(changes) >= 0.70
        and average <= -2
    ):

        return {
            "type": "MARKET_BEARISH",
            "breadth": breadth,
            "average": average,
            "positive": positive,
            "negative": negative,
        }

    return None


# ============================================================
# SNAPSHOT
# ============================================================

def update_snapshots(
    data,
    memory,
):

    timestamp = time.time()

    for coin_id, symbol in COINS:

        coin = data.get(coin_id)

        if not coin:
            continue

        price_value = coin.get("usd")
        volume = coin.get("usd_24h_vol")

        if price_value is None:
            continue

        memory["snapshots"][symbol] = {
            "price": price_value,
            "volume": volume,
            "timestamp": timestamp,
        }


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(event):

    event_type = event["type"]

    if event_type == "PRICE_ANOMALY":

        movement = abs(
            event["movement"]
        )

        if movement >= 10:
            return 95

        if movement >= 7:
            return 90

        if movement >= 5:
            return 85

        return 75

    if event_type == "VOLUME_ANOMALY":

        ratio = event["ratio"]

        if ratio >= 5:
            return 95

        if ratio >= 3:
            return 90

        if ratio >= 2.5:
            return 85

        return 75

    if event_type == "MARKET_BULLISH":

        if (
            event["breadth"] >= 85
            and event["average"] >= 3
        ):
            return 94

        return 82

    if event_type == "MARKET_BEARISH":

        if (
            event["negative"] >= 16
            and event["average"] <= -3
        ):
            return 94

        return 82

    return 70


# ============================================================
# EMBED — PRICE ANOMALY
# ============================================================

def build_price_alert(event):

    movement = event["movement"]

    bullish = movement > 0

    direction = (
        "UPWARD"
        if bullish
        else "DOWNWARD"
    )

    emoji = "🟢" if bullish else "🔴"

    confidence = calculate_confidence(
        event
    )

    embed = discord.Embed(
        title="⚡ VEYL // AUTOMATION",
        description=(
            "```text\n"
            "AUTONOMOUS MARKET EVENT\n"
            "────────────────────────────────\n"
            "ENGINE       AUTOMATION\n"
            "EVENT        PRICE ANOMALY\n"
            f"ASSET        {event['symbol']}\n"
            f"DIRECTION    {direction}\n"
            "────────────────────────────────\n"
            "```"
        ),
        color=(
            discord.Color.green()
            if bullish
            else discord.Color.red()
        ),
    )

    embed.add_field(
        name="◈ MOVEMENT",
        value=(
            f"{emoji} **{event['symbol']}**\n"
            f"`{movement:+.2f}%`\n"
            f"Price `{format_price(event['price'])}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="🧠 CONFIDENCE",
        value=(
            f"`{confidence}/100`\n"
            "VEYL anomaly engine"
        ),
        inline=True,
    )

    embed.add_field(
        name="⚠ DETECTION",
        value=(
            "Movement exceeded the configured "
            "short-term anomaly threshold."
        ),
        inline=False,
    )

    embed.set_footer(
        text="VEYL • AUTOMATION • PHASE 6"
    )

    return embed


# ============================================================
# EMBED — VOLUME ANOMALY
# ============================================================

def build_volume_alert(event):

    confidence = calculate_confidence(
        event
    )

    embed = discord.Embed(
        title="🐋 VEYL // AUTOMATION",
        description=(
            "```text\n"
            "AUTONOMOUS MARKET EVENT\n"
            "────────────────────────────────\n"
            "ENGINE       AUTOMATION\n"
            "EVENT        VOLUME ANOMALY\n"
            f"ASSET        {event['symbol']}\n"
            "────────────────────────────────\n"
            "```"
        ),
        color=discord.Color.gold(),
    )

    embed.add_field(
        name="◈ VOLUME",
        value=(
            f"**{event['symbol']}**\n"
            f"`{format_money(event['volume'])}`\n"
            f"Previous `{format_money(event['previous_volume'])}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="⚡ ACTIVITY",
        value=(
            f"`{event['ratio']:.2f}×`\n"
            "above previous observation"
        ),
        inline=True,
    )

    embed.add_field(
        name="🧠 CONFIDENCE",
        value=f"`{confidence}/100`",
        inline=True,
    )

    embed.add_field(
        name="⚠ DETECTION",
        value=(
            "Trading activity increased "
            "significantly compared with the "
            "previous VEYL observation."
        ),
        inline=False,
    )

    embed.set_footer(
        text="VEYL • AUTOMATION • VOLUME ENGINE"
    )

    return embed


# ============================================================
# EMBED — MARKET EVENT
# ============================================================

def build_market_event(event):

    bullish = (
        event["type"]
        == "MARKET_BULLISH"
    )

    if bullish:

        title = "🟢 VEYL // MARKET EVENT"
        state = "BULLISH EXPANSION"
        color = discord.Color.green()

    else:

        title = "🔴 VEYL // MARKET EVENT"
        state = "BEARISH EXPANSION"
        color = discord.Color.red()

    confidence = calculate_confidence(
        event
    )

    embed = discord.Embed(
        title=title,
        description=(
            "```text\n"
            "AUTONOMOUS MARKET EVENT\n"
            "────────────────────────────────\n"
            "ENGINE       AUTOMATION\n"
            f"STATE        {state}\n"
            "────────────────────────────────\n"
            "```"
        ),
        color=color,
    )

    embed.add_field(
        name="🌐 MARKET BREADTH",
        value=(
            f"`{event['breadth']:.1f}%`\n"
            f"UP `{event['positive']}`\n"
            f"DOWN `{event['negative']}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="◈ MARKET AVERAGE",
        value=(
            f"`{event['average']:+.2f}%`"
        ),
        inline=True,
    )

    embed.add_field(
        name="🧠 CONFIDENCE",
        value=f"`{confidence}/100`",
        inline=True,
    )

    embed.add_field(
        name="VEYL READ",
        value=(
            "Broad market participation detected. "
            "The movement is occurring across a "
            "large portion of the tracked market."
        ),
        inline=False,
    )

    embed.set_footer(
        text="VEYL • AUTOMATION • MARKET BREADTH"
    )

    return embed


# ============================================================
# AUTOMATION COG
# ============================================================

class VeylAutomation(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.memory = load_memory()

        self.last_data = None

        self.ready_once = False

        self.automation_loop.start()

        print(
            "⚡ VEYL Automation activé."
        )

        print(
            f"   ├─ Interval : {CHECK_INTERVAL}s"
        )

        print(
            f"   ├─ Price threshold : "
            f"{PRICE_ALERT_THRESHOLD}%"
        )

        print(
            f"   ├─ Volume multiplier : "
            f"{VOLUME_ANOMALY_MULTIPLIER}x"
        )

        print(
            "   └─ Autonomous monitoring : ONLINE"
        )


    # ========================================================
    # CLEANUP
    # ========================================================

    def cog_unload(self):

        self.automation_loop.cancel()

        print(
            "⚡ VEYL Automation arrêté."
        )


    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        if self.ready_once:
            return

        self.ready_once = True

        print(
            "⚡ VEYL Automation connecté au Discord."
        )


    # ========================================================
    # MAIN LOOP
    # ========================================================

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def automation_loop(self):

        if not self.bot.is_ready():
            return

        data = await get_market_data()

        if not data:
            return

        # ----------------------------------------------------
        # First observation
        # ----------------------------------------------------

        if not self.memory["snapshots"]:

            update_snapshots(
                data,
                self.memory,
            )

            save_memory(
                self.memory
            )

            self.last_data = data

            print(
                "⚡ VEYL Automation : "
                "initial market snapshot created."
            )

            return

        # ----------------------------------------------------
        # Detect events
        # ----------------------------------------------------

        events = []

        price_events = detect_price_anomalies(
            data,
            self.memory,
        )

        volume_events = detect_volume_anomalies(
            data,
            self.memory,
        )

        market_event = detect_market_event(
            data
        )

        events.extend(
            price_events
        )

        events.extend(
            volume_events
        )

        if market_event:

            alert_key = (
                f"market:{market_event['type']}"
            )

            if alert_allowed(
                self.memory,
                alert_key,
            ):

                events.append(
                    market_event
                )

        # ----------------------------------------------------
        # Update memory
        # ----------------------------------------------------

        update_snapshots(
            data,
            self.memory,
        )

        save_memory(
            self.memory
        )

        self.last_data = data

        # ----------------------------------------------------
        # No events
        # ----------------------------------------------------

        if not events:

            print(
                "⚡ Automation scan • "
                "No significant event."
            )

            return

        # ----------------------------------------------------
        # Find Discord channel
        # ----------------------------------------------------

        channel = find_automation_channel(
            self.bot
        )

        if channel is None:

            print(
                f"⚠️ VEYL Automation : "
                f"channel '{AUTOMATION_CHANNEL}' "
                f"not found."
            )

            return

        # ----------------------------------------------------
        # Send events
        # ----------------------------------------------------

        for event in events:

            try:

                event_type = event["type"]

                if event_type == "PRICE_ANOMALY":

                    embed = build_price_alert(
                        event
                    )

                elif event_type == "VOLUME_ANOMALY":

                    embed = build_volume_alert(
                        event
                    )

                elif event_type in (
                    "MARKET_BULLISH",
                    "MARKET_BEARISH",
                ):

                    embed = build_market_event(
                        event
                    )

                else:

                    continue

                await channel.send(
                    embed=embed
                )

                print(
                    f"⚡ AUTOMATION EVENT • "
                    f"{event_type}"
                )

                # Small delay so multiple events
                # don't flood Discord simultaneously.
                await asyncio.sleep(1)

            except discord.HTTPException as error:

                print(
                    f"⚠️ Automation Discord error : "
                    f"{error}"
                )

            except Exception as error:

                print(
                    f"❌ Automation event error : "
                    f"{error}"
                )


    # ========================================================
    # LOOP READY
    # ========================================================

    @automation_loop.before_loop
    async def before_automation_loop(self):

        await self.bot.wait_until_ready()

        print(
            "⚡ VEYL Automation monitoring started."
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylAutomation(bot)
    )

    print(
        "   ✅ commands.automation"
    )
