import discord
from discord import app_commands
from discord.ext import commands

import aiohttp


# ============================================================
# VEYL INDEX
# ============================================================

class VeylIndex(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="index",
        description="View the top 25 cryptocurrencies by market cap."
    )
    async def index(self, interaction: discord.Interaction):

        await interaction.response.defer()

        url = "https://api.coingecko.com/api/v3/coins/markets"

        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 25,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url,
                    params=params,
                    timeout=15
                ) as response:

                    if response.status != 200:

                        await interaction.followup.send(
                            "❌ Unable to retrieve market data."
                        )

                        return

                    coins = await response.json()

            # =================================================
            # EMBED
            # =================================================

            embed = discord.Embed(
                title="📊 VEYL INDEX",
                description=(
                    "Top 25 cryptocurrencies by market capitalization."
                ),
                color=discord.Color.blurple()
            )

            lines = []

            medals = [
                "🥇",
                "🥈",
                "🥉"
            ]

            for i, coin in enumerate(coins, start=1):

                name = coin.get(
                    "name",
                    "Unknown"
                )

                symbol = coin.get(
                    "symbol",
                    "?"
                ).upper()

                price = coin.get(
                    "current_price",
                    0
                ) or 0

                change = coin.get(
                    "price_change_percentage_24h",
                    0
                ) or 0

                market_cap = coin.get(
                    "market_cap",
                    0
                ) or 0

                # Prix
                if price >= 1:

                    price_text = f"${price:,.2f}"

                else:

                    price_text = f"${price:.6f}"

                # Market cap
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

                # Variation
                if change >= 0:

                    change_text = (
                        f"🟢 +{change:.2f}%"
                    )

                else:

                    change_text = (
                        f"🔴 {change:.2f}%"
                    )

                if i <= 3:

                    rank = medals[i - 1]

                else:

                    rank = f"`{i:02}`"

                lines.append(
                    f"{rank} **{name}** · `{symbol}`\n"
                    f"　${price_text.replace('$', '')} "
                    f"· {change_text} "
                    f"· `{market_cap_text}`"
                )

            # Discord limite les embeds à 6000 caractères.
            # 25 lignes restent largement sous la limite.

            embed.description += "\n\n"
            embed.description += "\n\n".join(
                lines
            )

            embed.set_footer(
                text="VEYL • Market Data • CoinGecko"
            )

            await interaction.followup.send(
                embed=embed
            )

            print(
                "📊 VEYL Index envoyé."
            )

        except aiohttp.ClientError as error:

            print(
                f"❌ Erreur CoinGecko : {error}"
            )

            await interaction.followup.send(
                "❌ Market data temporarily unavailable."
            )

        except Exception as error:

            print(
                f"❌ VEYL Index error : {error}"
            )

            await interaction.followup.send(
                "❌ An error occurred while loading the index."
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylIndex(bot)
    )

    print(
        "📊 VEYL Index activé."
    )