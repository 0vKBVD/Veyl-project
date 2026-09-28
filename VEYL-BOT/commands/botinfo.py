import time

import discord
from discord import app_commands
from discord.ext import commands


class VeylBotInfo(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.start_time = time.time()

    @app_commands.command(
        name="botinfo",
        description="View information about VEYL."
    )
    async def botinfo(
        self,
        interaction: discord.Interaction
    ):

        uptime_seconds = int(
            time.time()
            - self.start_time
        )

        days, remainder = divmod(
            uptime_seconds,
            86400
        )

        hours, remainder = divmod(
            remainder,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )

        uptime = (
            f"{days}d "
            f"{hours}h "
            f"{minutes}m "
            f"{seconds}s"
        )

        embed = discord.Embed(
            title="🤖 VEYL",
            description=(
                "VEYL • On-Chain Intelligence"
            ),
            color=discord.Color.blurple()
        )

        if self.bot.user:

            embed.set_thumbnail(
                url=self.bot.user.display_avatar.url
            )

        embed.add_field(
            name="BOT",
            value=f"**{self.bot.user}**",
            inline=True
        )

        embed.add_field(
            name="SERVERS",
            value=f"**{len(self.bot.guilds)}**",
            inline=True
        )

        embed.add_field(
            name="LATENCY",
            value=(
                f"**{round(self.bot.latency * 1000)}ms**"
            ),
            inline=True
        )

        embed.add_field(
            name="UPTIME",
            value=f"**{uptime}**",
            inline=False
        )

        embed.add_field(
            name="COMMANDS",
            value=f"**{len(self.bot.tree.get_commands())}**",
            inline=True
        )

        embed.add_field(
            name="DISCORD.PY",
            value=f"`{discord.__version__}`",
            inline=True
        )

        embed.add_field(
            name="BOT ID",
            value=f"`{self.bot.user.id}`",
            inline=False
        )

        embed.set_footer(
            text="VEYL • System Information"
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        VeylBotInfo(bot)
    )

    print(
        "🤖 VEYL BotInfo activé."
    )
