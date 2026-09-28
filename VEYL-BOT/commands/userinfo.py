import discord
from discord import app_commands
from discord.ext import commands


class VeylUserInfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="userinfo",
        description="View information about a user."
    )
    @app_commands.describe(
        user="The user to inspect"
    )
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):

        created_timestamp = int(
            user.created_at.timestamp()
        )

        joined_timestamp = int(
            user.joined_at.timestamp()
        ) if user.joined_at else None

        roles = [
            role.mention
            for role in user.roles[1:]
        ]

        role_text = (
            ", ".join(roles[-10:])
            if roles
            else "None"
        )

        embed = discord.Embed(
            title=f"👤 {user.display_name}",
            description=(
                f"Information about {user.mention}"
            ),
            color=(
                user.color
                if user.color != discord.Color.default()
                else discord.Color.blurple()
            )
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.add_field(
            name="USERNAME",
            value=f"`{user.name}`",
            inline=True
        )

        embed.add_field(
            name="USER ID",
            value=f"`{user.id}`",
            inline=True
        )

        embed.add_field(
            name="BOT",
            value="Yes" if user.bot else "No",
            inline=True
        )

        embed.add_field(
            name="ACCOUNT CREATED",
            value=f"<t:{created_timestamp}:F>",
            inline=False
        )

        if joined_timestamp:

            embed.add_field(
                name="JOINED SERVER",
                value=f"<t:{joined_timestamp}:F>",
                inline=False
            )

        embed.add_field(
            name="ROLES",
            value=role_text,
            inline=False
        )

        embed.set_footer(
            text="VEYL • User Information"
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        VeylUserInfo(bot)
    )

    print(
        "👤 VEYL UserInfo activé."
    )

