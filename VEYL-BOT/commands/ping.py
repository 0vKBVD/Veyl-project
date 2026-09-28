import time

import discord
from discord import app_commands
from discord.ext import commands


class VeylPing(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check VEYL's latency."
    )
    async def ping(
        self,
        interaction: discord.Interaction
    ):

        start = time.perf_counter()

        await interaction.response.send_message(
            "🏓 Checking latency..."
        )

        end = time.perf_counter()

        response_latency = round(
            (end - start) * 1000
        )

        websocket_latency = round(
            self.bot.latency * 1000
        )

        embed = discord.Embed(
            title="🏓 VEYL PING",
            color=discord.Color.green()
        )

        embed.add_field(
            name="BOT LATENCY",
            value=f"**{response_latency}ms**",
            inline=True
        )

        embed.add_field(
            name="WEBSOCKET",
            value=f"**{websocket_latency}ms**",
            inline=True
        )

        embed.add_field(
            name="STATUS",
            value="🟢 **OPERATIONAL**",
            inline=False
        )

        embed.set_footer(
            text="VEYL • System"
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        VeylPing(bot)
    )

    print(
        "🏓 VEYL Ping activé."
    )
