import discord
from discord.ext import tasks
from datetime import datetime

from services.market import get_crypto_price_async


CHANNEL_ID = 1542846026325565460

# ID DU MESSAGE SOLANA
MESSAGE_ID = 1542864358319853672


class LiveSolana:

    def __init__(self, bot):

        self.bot = bot
        self.message = None

        self.update_price.start()

    def cog_unload(self):

        self.update_price.cancel()

    async def get_message(self):

        if self.message is not None:
            return self.message

        try:

            channel = await self.bot.fetch_channel(
                CHANNEL_ID
            )

            # Récupère directement le message connu
            if MESSAGE_ID != 0:

                try:

                    self.message = await channel.fetch_message(
                        MESSAGE_ID
                    )

                    print(
                        "✅ Message SOLANA retrouvé."
                    )

                    return self.message

                except discord.NotFound:

                    print(
                        "⚠️ Message SOLANA introuvable."
                    )

            # Sécurité : cherche un ancien message SOLANA
            async for message in channel.history(
                limit=20
            ):

                if message.author.id != self.bot.user.id:
                    continue

                if not message.embeds:
                    continue

                title = message.embeds[0].title

                if title and "SOLANA" in title:

                    self.message = message

                    print(
                        f"✅ Message SOLANA retrouvé "
                        f"(ID: {message.id})"
                    )

                    return message

            print(
                "⚠️ Aucun message SOLANA trouvé."
            )

            return None

        except Exception as error:

            print(
                f"❌ Erreur récupération message : {error}"
            )

            return None

    async def update_embed(self):

        data = await get_crypto_price_async(
            "solana"
        )

        if data is None:

            print(
                "❌ Impossible de récupérer le prix de Solana."
            )

            return

        price = data.get(
            "usd",
            0
        )

        change = data.get(
            "usd_24h_change",
            0
        ) or 0

        market_cap = data.get(
            "usd_market_cap",
            0
        ) or 0

        volume = data.get(
            "usd_24h_vol",
            0
        ) or 0

        # ==============================
        # COULEUR
        # ==============================

        if change >= 0:

            color = discord.Color.green()
            arrow = "▲"
            change_icon = "🟢"

        else:

            color = discord.Color.red()
            arrow = "▼"
            change_icon = "🔴"

        # ==============================
        # PRIX
        # ==============================

        if price >= 1:

            price_text = f"${price:,.2f}"

        else:

            price_text = f"${price:,.8f}"

        # ==============================
        # MARKET CAP
        # ==============================

        if market_cap >= 1_000_000_000:

            market_cap_text = (
                f"${market_cap / 1_000_000_000:.2f}B"
            )

        elif market_cap >= 1_000_000:

            market_cap_text = (
                f"${market_cap / 1_000_000:.2f}M"
            )

        else:

            market_cap_text = (
                f"${market_cap:,.0f}"
            )

        # ==============================
        # VOLUME
        # ==============================

        if volume >= 1_000_000_000:

            volume_text = (
                f"${volume / 1_000_000_000:.2f}B"
            )

        elif volume >= 1_000_000:

            volume_text = (
                f"${volume / 1_000_000:.2f}M"
            )

        else:

            volume_text = (
                f"${volume:,.0f}"
            )

        now = datetime.now().strftime(
            "%H:%M:%S"
        )

        # ==============================
        # EMBED
        # ==============================

        embed = discord.Embed(
            title="SOLANA  •  SOL",
            description=f"# {price_text}",
            color=color
        )

        embed.add_field(
            name="24H",
            value=(
                f"{change_icon} "
                f"**{arrow} {change:.2f}%**"
            ),
            inline=True
        )

        embed.add_field(
            name="MARKET CAP",
            value=f"**{market_cap_text}**",
            inline=True
        )

        embed.add_field(
            name="VOLUME 24H",
            value=f"**{volume_text}**",
            inline=True
        )

        embed.add_field(
            name="STATUS",
            value="🟢 **LIVE**",
            inline=False
        )

        embed.set_footer(
            text=(
                f"VEYL • Live Market Data • "
                f"Updated {now}"
            )
        )

        # ==============================
        # MESSAGE
        # ==============================

        message = await self.get_message()

        if message is None:

            channel = await self.bot.fetch_channel(
                CHANNEL_ID
            )

            self.message = await channel.send(
                embed=embed
            )

            print(
                f"✅ Message SOLANA créé "
                f"(ID: {self.message.id})"
            )

        else:

            await message.edit(
                embed=embed
            )

            print(
                f"🔄 SOL updated • "
                f"{price_text} • "
                f"{change:.2f}%"
            )

    @tasks.loop(seconds=60)
    async def update_price(self):

        try:

            await self.update_embed()

        except discord.NotFound:

            print(
                "❌ Message ou salon introuvable."
            )

            self.message = None

        except discord.Forbidden:

            print(
                "❌ VEYL n'a pas les permissions nécessaires."
            )

        except Exception as error:

            print(
                f"❌ Erreur Live SOL : {error}"
            )

    @update_price.before_loop
    async def before_update(self):

        await self.bot.wait_until_ready()


async def setup(bot):

    bot.live_solana = LiveSolana(bot)