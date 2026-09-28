import discord
from discord import app_commands
from discord.ext import commands


class VeylStats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stats",
        description="View your VEYL statistics."
    )
    async def stats(
        self,
        interaction: discord.Interaction
    ):

        user = interaction.user

        # Try to find XP / level data if the bot has it
        xp = 0
        level = 0

        # Compatible with common leaderboard implementations
        leaderboard = getattr(
            self.bot,
            "leaderboard",
            None
        )

        if leaderboard:

            try:
                data = leaderboard.get_user_data(
                    user.id
                )

                if data:

                    xp = data.get(
                        "xp",
                        0
                    )

                    level = data.get(
                        "level",
                        0
                    )

            except Exception:
                pass

        embed = discord.Embed(
            title="📊 VEYL STATS",
            description=(
                f"Statistics for **{user.display_name}**"
            ),
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.add_field(
            name="LEVEL",
            value=f"**{level}**",
            inline=True
        )

        embed.add_field(
            name="XP",
            value=f"**{xp:,}**",
            inline=True
        )

        embed.add_field(
            name="USER ID",
            value=f"`{user.id}`",
            inline=False
        )

        embed.set_footer(
            text="VEYL • Statistics"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        VeylStats(bot)
    )

    print(
        "📊 VEYL Stats activé."
    )

