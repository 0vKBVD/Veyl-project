import discord
from discord import app_commands
from discord.ext import commands


class VeylAvatar(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="avatar",
        description="View a user's avatar."
    )
    @app_commands.describe(
        user="The user whose avatar you want to view"
    )
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.User = None
    ):

        if user is None:
            user = interaction.user

        embed = discord.Embed(
            title=f"🖼️ {user.display_name}'s Avatar",
            color=discord.Color.blurple()
        )

        embed.set_image(
            url=user.display_avatar.url
        )

        embed.add_field(
            name="USER",
            value=user.mention,
            inline=True
        )

        embed.add_field(
            name="USER ID",
            value=f"`{user.id}`",
            inline=True
        )

        embed.set_footer(
            text="VEYL • Avatar"
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        VeylAvatar(bot)
    )

    print(
        "🖼️ VEYL Avatar activé."
    )