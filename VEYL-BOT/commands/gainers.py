import asyncio
import time

import aiohttp
import discord
from discord.ext import commands, tasks


# ============================================================
# VEYL — GAINERS / LOSERS
# MARKET MOVERS ENGINE
# ============================================================

CHANNEL_ID = 1542846101227438130

# Mise à jour toutes les 10 minutes
CHECK_INTERVAL = 600

# Cooldown après un 429 CoinGecko
RATE_LIMIT_COOLDOWN = 600

# Nombre de cryptos analysées
CRYPTO_LIMIT = 100

# Timeout HTTP
REQUEST_TIMEOUT = 15

# CoinGecko endpoint
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
)


# ============================================================
# VEYL GAINERS
# ============================================================

class VeylGainers(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # ----------------------------------------------------
        # HTTP
        # ----------------------------------------------------

        self.session = None

        # Empêche deux requêtes CoinGecko simultanées
        self.request_lock = asyncio.Lock()

        # Timestamp jusqu'auquel CoinGecko est bloqué
        self.rate_limited_until = 0

        # ----------------------------------------------------
        # CACHE
        # ----------------------------------------------------

        self.cached_data = None
        self.cached_at = 0

        # ----------------------------------------------------
        # DISCORD MESSAGE
        # ----------------------------------------------------

        self.message = None

        # ----------------------------------------------------
        # LOOP
        # ----------------------------------------------------

        self.update_market.start()

        print(
            "📈 VEYL Gainers activé."
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
                    "User-Agent": (
                        "VEYL/2.0 "
                        "(Discord Market Engine)"
                    ),
                    "Accept": "application/json",
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
    # COINGECKO MARKET DATA
    # ========================================================

    async def get_market_data(self):

        # ----------------------------------------------------
        # LOCK
        # ----------------------------------------------------

        async with self.request_lock:

            now = time.time()

            # ------------------------------------------------
            # COOLDOWN
            # ------------------------------------------------

            if now < self.rate_limited_until:

                remaining = int(
                    self.rate_limited_until - now
                )

                minutes = max(
                    1,
                    remaining // 60
                )

                print(
                    "⏳ Gainers CoinGecko cooldown "
                    f"({minutes} min restantes)."
                )

                # Utilise le cache si disponible
                if self.cached_data:

                    print(
                        "   └─ Utilisation du cache."
                    )

                    return self.cached_data

                return None

            # ------------------------------------------------
            # PARAMÈTRES
            # ------------------------------------------------

            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": CRYPTO_LIMIT,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            }

            # ------------------------------------------------
            # REQUEST
            # ------------------------------------------------

            try:

                session = await self.get_session()

                async with session.get(
                    COINGECKO_URL,
                    params=params
                ) as response:

                    # ========================================
                    # RATE LIMIT
                    # ========================================

                    if response.status == 429:

                        retry_after = (
                            response.headers.get(
                                "Retry-After"
                            )
                        )

                        try:

                            retry_seconds = int(
                                retry_after
                            )

                        except (
                            TypeError,
                            ValueError
                        ):

                            retry_seconds = (
                                RATE_LIMIT_COOLDOWN
                            )

                        retry_seconds = max(
                            retry_seconds,
                            RATE_LIMIT_COOLDOWN
                        )

                        self.rate_limited_until = (
                            time.time()
                            + retry_seconds
                        )

                        print(
                            "⚠️ Gainers : "
                            "CoinGecko HTTP 429."
                        )

                        print(
                            "   └─ Cooldown : "
                            f"{retry_seconds // 60} minutes."
                        )

                        if self.cached_data:

                            print(
                                "   └─ Cache utilisé."
                            )

                            return self.cached_data

                        return None

                    # ========================================
                    # AUTRE ERREUR
                    # ========================================

                    if response.status != 200:

                        print(
                            "⚠️ Gainers : "
                            f"CoinGecko HTTP "
                            f"{response.status}."
                        )

                        if self.cached_data:

                            print(
                                "   └─ Cache utilisé."
                            )

                            return self.cached_data

                        return None

                    # ========================================
                    # JSON
                    # ========================================

                    data = await response.json()

                    if not isinstance(
                        data,
                        list
                    ):

                        print(
                            "⚠️ Gainers : "
                            "réponse CoinGecko invalide."
                        )

                        return (
                            self.cached_data
                        )

                    if not data:

                        print(
                            "⚠️ Gainers : "
                            "CoinGecko a retourné "
                            "une liste vide."
                        )

                        return (
                            self.cached_data
                        )

                    # ========================================
                    # CACHE
                    # ========================================

                    self.cached_data = data
                    self.cached_at = time.time()

                    print(
                        f"📡 Gainers : "
                        f"{len(data)} assets reçus."
                    )

                    return data

            # ------------------------------------------------
            # TIMEOUT
            # ------------------------------------------------

            except asyncio.TimeoutError:

                print(
                    "⚠️ Gainers : "
                    "timeout CoinGecko."
                )

                return self.cached_data

            # ------------------------------------------------
            # HTTP ERROR
            # ------------------------------------------------

            except aiohttp.ClientError as error:

                print(
                    "⚠️ Gainers : "
                    f"erreur HTTP : {error}"
                )

                return self.cached_data

            # ------------------------------------------------
            # UNKNOWN ERROR
            # ------------------------------------------------

            except Exception as error:

                print(
                    "❌ Gainers : "
                    f"erreur : {error}"
                )

                return self.cached_data


    # ========================================================
    # FORMAT PRICE
    # ========================================================

    @staticmethod
    def format_price(price):

        if price is None:

            return "N/A"

        try:

            price = float(price)

        except (
            TypeError,
            ValueError
        ):

            return "N/A"

        if price >= 1_000_000:

            return f"${price:,.0f}"

        if price >= 1:

            return f"${price:,.2f}"

        if price >= 0.01:

            return f"${price:,.4f}"

        return f"${price:,.8f}"


    # ========================================================
    # GET EXISTING MESSAGE
    # ========================================================

    async def get_message(self):

        if self.message is not None:

            return self.message

        try:

            channel = await self.bot.fetch_channel(
                CHANNEL_ID
            )

            if not hasattr(
                channel,
                "history"
            ):

                print(
                    "⚠️ Gainers : "
                    "le salon ne permet pas "
                    "la lecture de l'historique."
                )

                return None

            async for message in channel.history(
                limit=30
            ):

                # ------------------------------------------------
                # Seulement les messages de VEYL
                # ------------------------------------------------

                if (
                    self.bot.user
                    and message.author.id
                    != self.bot.user.id
                ):

                    continue

                # ------------------------------------------------
                # Seulement les embeds
                # ------------------------------------------------

                if not message.embeds:

                    continue

                title = (
                    message.embeds[0].title
                )

                if title == (
                    "VEYL • MARKET MOVERS"
                ):

                    self.message = message

                    print(
                        "✅ Message Gainers retrouvé."
                    )

                    return message

            return None

        except discord.NotFound:

            print(
                "⚠️ Gainers : "
                "salon introuvable."
            )

            return None

        except discord.Forbidden:

            print(
                "❌ Gainers : "
                "permissions insuffisantes."
            )

            return None

        except discord.HTTPException as error:

            print(
                f"⚠️ Gainers Discord : {error}"
            )

            return None

        except Exception as error:

            print(
                "❌ Gainers : "
                f"erreur récupération message : "
                f"{error}"
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
        # VALID ASSETS
        # ----------------------------------------------------

        valid = []

        for coin in data:

            if not isinstance(
                coin,
                dict
            ):

                continue

            change = coin.get(
                "price_change_percentage_24h"
            )

            try:

                change = float(change)

            except (
                TypeError,
                ValueError
            ):

                continue

            valid.append(
                (
                    change,
                    coin
                )
            )

        if not valid:

            return None

        # ----------------------------------------------------
        # SORT
        # ----------------------------------------------------

        gainers = sorted(
            valid,
            key=lambda item: item[0],
            reverse=True
        )[:5]

        losers = sorted(
            valid,
            key=lambda item: item[0]
        )[:5]

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="VEYL • MARKET MOVERS",
            description=(
                "Live market performance • "
                "Top 100 assets • 24H"
            ),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )

        # ====================================================
        # GAINERS
        # ====================================================

        gainers_text = []

        for index, (
            change,
            coin
        ) in enumerate(
            gainers,
            start=1
        ):

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

            gainers_text.append(
                f"**{index}. {name}** "
                f"`{symbol}`\n"
                f"↗ **+{change:.2f}%** "
                f"• {self.format_price(price)}"
            )

        embed.add_field(
            name="🟢 GAINERS",
            value=(
                "\n\n".join(
                    gainers_text
                )
                if gainers_text
                else "No data."
            ),
            inline=True,
        )

        # ====================================================
        # LOSERS
        # ====================================================

        losers_text = []

        for index, (
            change,
            coin
        ) in enumerate(
            losers,
            start=1
        ):

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

            losers_text.append(
                f"**{index}. {name}** "
                f"`{symbol}`\n"
                f"↘ **{change:.2f}%** "
                f"• {self.format_price(price)}"
            )

        embed.add_field(
            name="🔴 LOSERS",
            value=(
                "\n\n".join(
                    losers_text
                )
                if losers_text
                else "No data."
            ),
            inline=True,
        )

        # ====================================================
        # ENGINE STATUS
        # ====================================================

        cache_age = (
            int(time.time() - self.cached_at)
            if self.cached_at
            else 0
        )

        embed.add_field(
            name="◈ VEYL MARKET ENGINE",
            value=(
                "◆ **SOURCE**    `COINGECKO`\n"
                "◆ **ASSETS**    `100`\n"
                "◆ **INTERVAL**  `10 MIN`\n"
                f"◆ **CACHE**     `{cache_age}s OLD`\n"
                "◆ **STATUS**    `ONLINE`"
            ),
            inline=False,
        )

        embed.set_footer(
            text=(
                "VEYL • MARKET DATA • "
                "10 MIN UPDATES"
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
                    "✅ Message Gainers créé "
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
                "🔄 Gainers / Losers updated."
            )

        except discord.NotFound:

            print(
                "⚠️ Message Gainers "
                "supprimé. Recherche suivante."
            )

            self.message = None

        except discord.Forbidden:

            print(
                "❌ VEYL : permissions "
                "insuffisantes pour Gainers."
            )

        except discord.HTTPException as error:

            if error.status == 429:

                print(
                    "⚠️ Discord rate-limit "
                    "sur Gainers."
                )

                # Ne pas spammer Discord
                self.message = None

            else:

                print(
                    "⚠️ Gainers Discord HTTP : "
                    f"{error}"
                )

        except Exception as error:

            print(
                "❌ Gainers update error : "
                f"{error}"
            )


    # ========================================================
    # MAIN LOOP
    # ========================================================

    @tasks.loop(
        seconds=CHECK_INTERVAL
    )
    async def update_market(self):

        try:

            data = await self.get_market_data()

            if not data:

                print(
                    "⚠️ Gainers : "
                    "aucune donnée disponible."
                )

                return

            embed = self.create_embed(
                data
            )

            if embed is None:

                print(
                    "⚠️ Gainers : "
                    "impossible de créer l'embed."
                )

                return

            await self.update_message(
                embed
            )

        except asyncio.CancelledError:

            raise

        except Exception as error:

            print(
                "❌ VEYL Gainers error : "
                f"{error}"
            )


    # ========================================================
    # BEFORE LOOP
    # ========================================================

    @update_market.before_loop
    async def before_update_market(
        self
    ):

        await self.bot.wait_until_ready()

        print(
            "📈 VEYL Gainers démarré."
        )

        print(
            f"   ├─ Interval : "
            f"{CHECK_INTERVAL // 60} minutes"
        )

        print(
            f"   ├─ Coins : "
            f"{CRYPTO_LIMIT}"
        )

        print(
            "   ├─ CoinGecko cooldown : "
            f"{RATE_LIMIT_COOLDOWN // 60} minutes"
        )

        print(
            "   └─ Cache : ACTIVE"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        VeylGainers(bot)
    )

    print(
        "   ✅ commands.gainers"
    )