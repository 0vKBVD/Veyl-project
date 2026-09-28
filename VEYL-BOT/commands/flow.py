import asyncio
import time

import aiohttp
import discord
from discord.ext import commands, tasks


# ============================================================
# VEYL FLOW V2
# ============================================================

FLOW_CHANNEL_ID = 1542942318527778907

# Intervalle entre deux scans
CHECK_INTERVAL = 60

# Seuils minimum
BTC_MIN_VALUE_USD = 1_000_000
SOL_MIN_VALUE_USD = 500_000


# ============================================================
# API
# ============================================================

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
)

MEMPOOL_URL = (
    "https://mempool.space/api/mempool/recent"
)

SOLANA_RPC = (
    "https://api.mainnet-beta.solana.com"
)


# ============================================================
# CONFIG
# ============================================================

# Adresse système Solana.
# Utilisée comme point d'entrée pour récupérer
# les dernières signatures du réseau.
SOLANA_ADDRESS = (
    "11111111111111111111111111111111"
)

LAMPORTS_PER_SOL = 1_000_000_000

REQUEST_TIMEOUT = 15

MAX_SEEN = 5000

# Pause après un HTTP 429 du RPC Solana
SOLANA_BACKOFF = 60


# ============================================================
# VEYL FLOW
# ============================================================

class VeylFlow(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.seen_btc = set()
        self.seen_sol = set()

        self.solana_blocked_until = 0

        self.session = None

        self.monitor_flow.start()

        print("🐋 VEYL Flow initialisé.")

    # ========================================================
    # SESSION
    # ========================================================

    async def get_session(self):

        if self.session is None or self.session.closed:

            timeout = aiohttp.ClientTimeout(
                total=REQUEST_TIMEOUT
            )

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "VEYL/2.0"
                }
            )

        return self.session

    # ========================================================
    # CLEANUP
    # ========================================================

    def cog_unload(self):

        self.monitor_flow.cancel()

        if self.session and not self.session.closed:

            asyncio.create_task(
                self.session.close()
            )

    # ========================================================
    # HTTP GET JSON
    # ========================================================

    async def get_json(
        self,
        url,
        params=None
    ):

        try:

            session = await self.get_session()

            async with session.get(
                url,
                params=params
            ) as response:

                if response.status == 429:

                    print(
                        f"⚠️ HTTP 429 : {url}"
                    )

                    return None, 429

                if response.status != 200:

                    print(
                        f"⚠️ HTTP {response.status} : {url}"
                    )

                    return None, response.status

                return await response.json(), 200

        except asyncio.TimeoutError:

            print(
                f"⚠️ Timeout HTTP : {url}"
            )

            return None, 408

        except aiohttp.ClientError as error:

            print(
                f"⚠️ HTTP error : {error}"
            )

            return None, 0

        except Exception as error:

            print(
                f"❌ HTTP error : {error}"
            )

            return None, 0

    # ========================================================
    # PRICE
    # ========================================================

    async def get_prices(self):

        data, status = await self.get_json(
            COINGECKO_URL,
            {
                "ids": "bitcoin,solana",
                "vs_currencies": "usd"
            }
        )

        if status != 200 or not data:

            return None

        return data

    # ========================================================
    # BITCOIN
    # ========================================================

    async def get_btc_transactions(self):

        data, status = await self.get_json(
            MEMPOOL_URL
        )

        if status != 200 or not data:

            return []

        if not isinstance(data, list):

            return []

        return data

    # ========================================================
    # SOLANA RPC
    # ========================================================

    async def solana_rpc(
        self,
        method,
        params
    ):

        now = time.time()

        # Protection contre les 429
        if now < self.solana_blocked_until:

            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        try:

            session = await self.get_session()

            async with session.post(
                SOLANA_RPC,
                json=payload
            ) as response:

                if response.status == 429:

                    self.solana_blocked_until = (
                        time.time() + SOLANA_BACKOFF
                    )

                    print(
                        "⚠️ Solana RPC limité."
                    )

                    print(
                        f"   └─ Pause : {SOLANA_BACKOFF}s"
                    )

                    return None

                if response.status != 200:

                    print(
                        f"⚠️ Solana RPC HTTP "
                        f"{response.status}"
                    )

                    return None

                data = await response.json()

                if "error" in data:

                    print(
                        f"⚠️ Solana RPC error : "
                        f"{data['error']}"
                    )

                    return None

                return data.get(
                    "result"
                )

        except asyncio.TimeoutError:

            print(
                "⚠️ Solana RPC timeout."
            )

            return None

        except aiohttp.ClientError as error:

            print(
                f"⚠️ Solana RPC connection error : "
                f"{error}"
            )

            return None

        except Exception as error:

            print(
                f"❌ Solana RPC error : {error}"
            )

            return None

    # ========================================================
    # SOLANA SIGNATURES
    # ========================================================

    async def get_sol_transactions(self):

        result = await self.solana_rpc(
            "getSignaturesForAddress",
            [
                SOLANA_ADDRESS,
                {
                    "limit": 10,
                    "commitment": "confirmed"
                }
            ]
        )

        if not result:

            return []

        return result

    # ========================================================
    # SOLANA TRANSACTION DETAILS
    # ========================================================

    async def get_sol_transaction(
        self,
        signature
    ):

        result = await self.solana_rpc(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        )

        return result

    # ========================================================
    # CALCULATE SOL MOVEMENT
    # ========================================================

    def calculate_sol_movement(
        self,
        transaction
    ):

        if not transaction:

            return 0

        meta = transaction.get(
            "meta"
        )

        if not meta:

            return 0

        pre_balances = meta.get(
            "preBalances",
            []
        )

        post_balances = meta.get(
            "postBalances",
            []
        )

        if not pre_balances or not post_balances:

            return 0

        total_movement = 0

        count = min(
            len(pre_balances),
            len(post_balances)
        )

        for i in range(count):

            difference = (
                post_balances[i]
                - pre_balances[i]
            )

            if difference < 0:

                total_movement += abs(
                    difference
                )

        return (
            total_movement
            / LAMPORTS_PER_SOL
        )

    # ========================================================
    # BTC ALERT
    # ========================================================

    async def send_btc_alert(
        self,
        tx,
        btc_price
    ):

        txid = tx.get(
            "txid"
        )

        if not txid:

            return

        if txid in self.seen_btc:

            return

        value_sats = tx.get(
            "value",
            0
        )

        btc_amount = (
            value_sats
            / 100_000_000
        )

        usd_value = (
            btc_amount
            * btc_price
        )

        if usd_value < BTC_MIN_VALUE_USD:

            return

        self.seen_btc.add(
            txid
        )

        self.trim_cache(
            self.seen_btc
        )

        embed = discord.Embed(
            title="🐋 VEYL FLOW",
            description=(
                "**Large Bitcoin transaction detected.**"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="NETWORK",
            value="₿ Bitcoin",
            inline=True
        )

        embed.add_field(
            name="VALUE",
            value=(
                f"**{btc_amount:,.2f} BTC**\n"
                f"${usd_value:,.0f}"
            ),
            inline=True
        )

        embed.add_field(
            name="TRANSACTION",
            value=(
                f"`{txid[:16]}...`"
            ),
            inline=False
        )

        embed.add_field(
            name="STATUS",
            value="🟢 **DETECTED**",
            inline=False
        )

        embed.url = (
            f"https://mempool.space/tx/{txid}"
        )

        embed.set_footer(
            text="VEYL • On-Chain Intelligence"
        )

        await self.send_alert(
            embed
        )

        print(
            f"🐋 BTC Flow | "
            f"{btc_amount:.2f} BTC | "
            f"${usd_value:,.0f}"
        )

    # ========================================================
    # SOLANA ALERT
    # ========================================================

    async def send_sol_alert(
        self,
        signature,
        sol_amount,
        sol_price
    ):

        usd_value = (
            sol_amount
            * sol_price
        )

        if usd_value < SOL_MIN_VALUE_USD:

            return

        if signature in self.seen_sol:

            return

        self.seen_sol.add(
            signature
        )

        self.trim_cache(
            self.seen_sol
        )

        embed = discord.Embed(
            title="🐋 VEYL FLOW",
            description=(
                "**Large Solana transaction detected.**"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="NETWORK",
            value="◎ Solana",
            inline=True
        )

        embed.add_field(
            name="VALUE",
            value=(
                f"**{sol_amount:,.2f} SOL**\n"
                f"${usd_value:,.0f}"
            ),
            inline=True
        )

        embed.add_field(
            name="TRANSACTION",
            value=(
                f"`{signature[:16]}...`"
            ),
            inline=False
        )

        embed.add_field(
            name="STATUS",
            value="🟢 **DETECTED**",
            inline=False
        )

        embed.url = (
            "https://solscan.io/tx/"
            + signature
        )

        embed.set_footer(
            text="VEYL • On-Chain Intelligence"
        )

        await self.send_alert(
            embed
        )

        print(
            f"🐋 SOL Flow | "
            f"{sol_amount:,.2f} SOL | "
            f"${usd_value:,.0f}"
        )

    # ========================================================
    # PROCESS SOLANA
    # ========================================================

    async def process_sol_transactions(
        self,
        transactions,
        sol_price
    ):

        if not transactions:

            return

        for item in transactions:

            signature = item.get(
                "signature"
            )

            if not signature:

                continue

            if signature in self.seen_sol:

                continue

            # Marque immédiatement la signature
            # pour éviter les doublons.
            self.seen_sol.add(
                signature
            )

            transaction = (
                await self.get_sol_transaction(
                    signature
                )
            )

            if not transaction:

                continue

            sol_amount = (
                self.calculate_sol_movement(
                    transaction
                )
            )

            if sol_amount <= 0:

                continue

            usd_value = (
                sol_amount
                * sol_price
            )

            if usd_value < SOL_MIN_VALUE_USD:

                continue

            # On retire temporairement la signature
            # pour laisser send_sol_alert() gérer le cache.
            self.seen_sol.discard(
                signature
            )

            await self.send_sol_alert(
                signature,
                sol_amount,
                sol_price
            )

            # Petite pause entre les requêtes RPC
            await asyncio.sleep(0.5)

    # ========================================================
    # SEND ALERT
    # ========================================================

    async def send_alert(
        self,
        embed
    ):

        try:

            channel = self.bot.get_channel(
                FLOW_CHANNEL_ID
            )

            if channel is None:

                channel = await self.bot.fetch_channel(
                    FLOW_CHANNEL_ID
                )

            await channel.send(
                embed=embed
            )

        except discord.Forbidden:

            print(
                "❌ VEYL n'a pas la permission "
                "d'écrire dans #veyl-flow."
            )

        except discord.NotFound:

            print(
                "❌ Salon VEYL Flow introuvable."
            )

        except Exception as error:

            print(
                f"❌ Flow Discord error : {error}"
            )

    # ========================================================
    # CACHE
    # ========================================================

    def trim_cache(
        self,
        cache
    ):

        if len(cache) <= MAX_SEEN:

            return

        items = list(cache)

        cache.clear()

        cache.update(
            items[-MAX_SEEN // 2:]
        )

    # ========================================================
    # MONITOR
    # ========================================================

    @tasks.loop(
        seconds=CHECK_INTERVAL
    )
    async def monitor_flow(self):

        try:

            prices = await self.get_prices()

            if not prices:

                print(
                    "⚠️ VEYL Flow : "
                    "prix indisponibles."
                )

                return

            btc_price = (
                prices
                .get("bitcoin", {})
                .get("usd")
            )

            sol_price = (
                prices
                .get("solana", {})
                .get("usd")
            )

            if not btc_price or not sol_price:

                return

            # =================================================
            # BTC
            # =================================================

            btc_transactions = (
                await self.get_btc_transactions()
            )

            for tx in btc_transactions:

                await self.send_btc_alert(
                    tx,
                    btc_price
                )

            # =================================================
            # SOLANA
            # =================================================

            sol_transactions = (
                await self.get_sol_transactions()
            )

            await self.process_sol_transactions(
                sol_transactions,
                sol_price
            )

        except Exception as error:

            print(
                f"❌ VEYL Flow error : {error}"
            )

    # ========================================================
    # BEFORE LOOP
    # ========================================================

    @monitor_flow.before_loop
    async def before_monitor_flow(self):

        await self.bot.wait_until_ready()

        print(
            "🐋 VEYL Flow démarré."
        )

        print(
            f"   ├─ BTC threshold : "
            f"${BTC_MIN_VALUE_USD:,.0f}"
        )

        print(
            f"   ├─ SOL threshold : "
            f"${SOL_MIN_VALUE_USD:,.0f}"
        )

        print(
            f"   ├─ Interval : "
            f"{CHECK_INTERVAL}s"
        )

        print(
            "   └─ Solana RPC : actif"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylFlow(bot)
    )

    print(
        "🐋 VEYL Flow activé."
    )