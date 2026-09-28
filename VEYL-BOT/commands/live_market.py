import asyncio
import time

import aiohttp
import discord
from discord.ext import commands, tasks


# ============================================================
# VEYL LIVE MARKET
# ============================================================

CHANNEL_ID = 1542845724679479366
# ↑ REMPLACE 0 PAR L'ID DU SALON #live-market

UPDATE_INTERVAL = 60
REQUEST_TIMEOUT = 15

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
)

COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "binancecoin",
    "ripple",
    "cardano",
    "avalanche-2",
    "chainlink",
    "sui",
    "dogecoin",
]


# ============================================================
# VEYL LIVE MARKET
# ============================================================

class VeylLiveMarket(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.session = None
        self.message = None

        self.rate_limited_until = 0

        self.update_market.start()

        print(
            "📡 VEYL Live Market activé."
        )

    # ========================================================
    # SESSION
    # ========================================================

    async def get_session(self):

        if (
            self.session is None
            or self.session.closed
        ):

            timeout = aiohttp.ClientTimeout(
                total=REQUEST_TIMEOUT
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "VEYL-Live-Market/1.0"
                }
            )

        return self.session

    # ========================================================
    # CLEANUP
    # ========================================================

    def cog_unload(self):

        self.update_market.cancel()

        if (
            self.session
            and not self.session.closed
        ):

            asyncio.create_task(
                self.session.close()
            )

    # ========================================================
    # COINGECKO
    # ========================================================

    async def get_market_data(self):

        # ----------------------------------------------------
        # RATE LIMIT PROTECTION
        # ----------------------------------------------------

        if time.time() < self.rate_limited_until:

            remaining = int(
                self.rate_limited_until
                - time.time()
            )

            print(
                f"⏳ Live Market cooldown "
                f"({remaining}s)"
            )

            return None

        params = {
            "vs_currency": "usd",
            "ids": ",".join(COINS),
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        try:

            session = await self.get_session()

            async with session.get(
                COINGECKO_URL,
                params=params
            ) as response:

                # ==========================================
                # RATE LIMIT
                # ==========================================

                if response.status == 429:

                    self.rate_limited_until = (
                        time.time() + 600
                    )

                    print(
                        "⚠️ Live Market : "
                        "CoinGecko HTTP 429."
                    )

                    print(
                        "   └─ Cooldown : 10 minutes."
                    )

                    return None

                # ==========================================
                # OTHER ERROR
                # ==========================================

                if response.status != 200:

                    print(
                        f"⚠️ Live Market : "
                        f"HTTP {response.status}"
                    )

                    return None

                data = await response.json()

                if not isinstance(
                    data,
                    list
                ):

                    return None

                return data

        except asyncio.TimeoutError:

            print(
                "⚠️ Live Market : timeout."
            )

        except aiohttp.ClientError as error:

            print(
                f"⚠️ Live Market HTTP error : "
                f"{error}"
            )

        except Exception as error:

            print(
                f"❌ Live Market error : "
                f"{type(error).__name__}: {error}"
            )

        return None

    # ========================================================
    # FORMAT PRICE
    # ========================================================

    def format_price(
        self,
        price
    ):

        if price is None:

            return "N/A"

        if price >= 1000:

            return f"${price:,.2f}"

        if price >= 1:

            return f"${price:,.2f}"

        if price >= 0.01:

            return f"${price:.4f}"

        return f"${price:.8f}"

    # ========================================================
    # FORMAT MARKET CAP
    # ========================================================

    def format_market_cap(
        self,
        value
    ):

        if value is None:

            return "N/A"

        if value >= 1_000_000_000_000:

            return (
                f"${value / 1_000_000_000_000:.2f}T"
            )

        if value >= 1_000_000_000:

            return (
                f"${value / 1_000_000_000:.2f}B"
            )

        if value >= 1_000_000:

            return (
                f"${value / 1_000_000:.2f}M"
            )

        return f"${value:,.0f}"

    # ========================================================
    # FORMAT CHANGE
    # ========================================================

    def format_change(
        self,
        change
    ):

        if change is None:

            return "N/A"

        try:

            change = float(change)

        except (
            TypeError,
            ValueError
        ):

            return "N/A"

        if change > 0:

            return f"↗ +{change:.2f}%"

        if change < 0:

            return f"↘ {change:.2f}%"

        return "→ 0.00%"

    # ========================================================
    # CHANGE ICON
    # ========================================================

    def change_icon(
        self,
        change
    ):

        if change is None:

            return "◆"

        if change > 0:

            return "▲"

        if change < 0:

            return "▼"

        return "◆"

    # ========================================================
    # FIND MESSAGE
    # ========================================================

    async def get_message(self):

        if self.message is not None:

            return self.message

        try:

            channel = await self.bot.fetch_channel(
                CHANNEL_ID
            )

            async for message in channel.history(
                limit=30
            ):

                if message.author.id != self.bot.user.id:

                    continue

                if not message.embeds:

                    continue

                title = message.embeds[0].title

                if title == "◈ VEYL / LIVE MARKET":

                    self.message = message

                    print(
                        "✅ Live Market message retrouvé."
                    )

                    return message

        except Exception as error:

            print(
                f"❌ Live Market : "
                f"erreur récupération message : {error}"
            )

        return None

    # ========================================================
    # CREATE EMBED
    # ========================================================

    def create_embed(
        self,
        data
    ):

        if not data:

            return None

        # ----------------------------------------------------
        # DICTIONARY
        # ----------------------------------------------------

        markets = {}

        for coin in data:

            coin_id = coin.get(
                "id"
            )

            if coin_id:

                markets[coin_id] = coin

        # ----------------------------------------------------
        # MARKET ROWS
        # ----------------------------------------------------

        rows = []

        for coin_id in COINS:

            coin = markets.get(
                coin_id
            )

            if not coin:

                continue

            name = coin.get(
                "name",
                "Unknown"
            )

            symbol = coin.get(
                "symbol",
                ""
            ).upper()

            price = coin.get(
                "current_price"
            )

            change = coin.get(
                "price_change_percentage_24h"
            )

            market_cap = coin.get(
                "market_cap"
            )

            icon = self.change_icon(
                change
            )

            change_text = self.format_change(
                change
            )

            price_text = self.format_price(
                price
            )

            rows.append(
                f"{icon} **{name}** `"
                f"{symbol}`\n"
                f"   `{price_text}`  •  "
                f"**{change_text}**"
            )

        if not rows:

            return None

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(

            title="◈ VEYL / LIVE MARKET",

            description=(
                "**REAL-TIME DIGITAL ASSET MONITOR**\n"
                "Live market prices and 24H performance."
            ),

            color=0xF2F2F2
        )

        embed.add_field(

            name="MARKET DATA",

            value="\n\n".join(rows),

            inline=False
        )

        # ----------------------------------------------------
        # MARKET SUMMARY
        # ----------------------------------------------------

        total_coins = len(
            markets
        )

        positive = 0
        negative = 0

        for coin in markets.values():

            change = coin.get(
                "price_change_percentage_24h"
            )

            if change is None:

                continue

            if change > 0:

                positive += 1

            elif change < 0:

                negative += 1

        embed.add_field(

            name="MARKET BREADTH",

            value=(
                f"▲ **{positive}** positive\n"
                f"▼ **{negative}** negative\n"
                f"◆ **{total_coins}** tracked assets"
            ),

            inline=True
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        embed.add_field(

            name="ENGINE STATUS",

            value=(
                "◆ **MARKET ENGINE** `ONLINE`\n"
                "◆ **DATA FEED** `LIVE`\n"
                "◆ **RATE LIMIT** `PROTECTED`"
            ),

            inline=True
        )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        embed.set_footer(

            text=(
                "VEYL • LIVE MARKET • "
                "60s UPDATE INTERVAL • COINGECKO"
            )

        )

        return embed

    # ========================================================
    # UPDATE MESSAGE
    # ========================================================

    async def update_message(
        self,
        embed
    ):

        if embed is None:

            return

        try:

            message = await self.get_message()

            # ------------------------------------------------
            # CREATE
            # ------------------------------------------------

            if message is None:

                channel = await self.bot.fetch_channel(
                    CHANNEL_ID
                )

                self.message = await channel.send(
                    embed=embed
                )

                print(
                    f"📡 Live Market message créé "
                    f"(ID: {self.message.id})"
                )

                return

            # ------------------------------------------------
            # EDIT
            # ------------------------------------------------

            await message.edit(
                embed=embed
            )

            print(
                "🔄 VEYL Live Market updated."
            )

        except discord.NotFound:

            self.message = None

            print(
                "⚠️ Live Market message introuvable."
            )

        except discord.Forbidden:

            print(
                "❌ VEYL n'a pas les permissions "
                "sur #live-market."
            )

        except discord.HTTPException as error:

            print(
                f"⚠️ Discord Live Market error : "
                f"{error}"
            )

        except Exception as error:

            print(
                f"❌ Live Market update error : "
                f"{error}"
            )

    # ========================================================
    # MAIN LOOP
    # ========================================================

    @tasks.loop(
        seconds=UPDATE_INTERVAL
    )
    async def update_market(self):

        try:

            data = await self.get_market_data()

            if not data:

                return

            embed = self.create_embed(
                data
            )

            await self.update_message(
                embed
            )

        except Exception as error:

            print(
                f"❌ VEYL Live Market error : "
                f"{type(error).__name__}: {error}"
            )

    # ========================================================
    # BEFORE LOOP
    # ========================================================

    @update_market.before_loop
    async def before_update_market(self):

        await self.bot.wait_until_ready()

        print(
            "📡 VEYL Live Market démarré."
        )

        print(
            f"   ├─ Interval : "
            f"{UPDATE_INTERVAL}s"
        )

        print(
            f"   ├─ Assets : "
            f"{len(COINS)}"
        )

        print(
            "   └─ Rate-limit protection : ACTIVE"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylLiveMarket(bot)
    )

    print(
        "📡 VEYL Live Market extension chargée."
    )