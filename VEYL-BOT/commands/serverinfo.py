import discord
from discord import app_commands
from discord.ext import commands


class VeylServerInfo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="serverinfo",
        description="View information about the server."
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

            return

        created_timestamp = int(
            guild.created_at.timestamp()
        )

        embed = discord.Embed(
            title=f"🏛️ {guild.name}",
            description="Server information",
            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(
            name="OWNER",
            value=f"<@{guild.owner_id}>",
            inline=True
        )

        embed.add_field(
            name="MEMBERS",
            value=f"**{guild.member_count:,}**",
            inline=True
        )

        embed.add_field(
            name="CHANNELS",
            value=f"**{len(guild.channels)}**",
            inline=True
        )

        embed.add_field(
            name="TEXT CHANNELS",
            value=f"**{len(guild.text_channels)}**",
            inline=True
        )

        embed.add_field(
            name="VOICE CHANNELS",
            value=f"**{len(guild.voice_channels)}**",
            inline=True
        )

        embed.add_field(
            name="ROLES",
            value=f"**{len(guild.roles)}**",
            inline=True
        )

        embed.add_field(
            name="SERVER ID",
            value=f"`{guild.id}`",
            inline=False
        )

        embed.add_field(
            name="CREATED",
            value=f"<t:{created_timestamp}:F>",
            inline=False
        )

        embed.set_footer(
            text="VEYL • Server Information"
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        VeylServerInfo(bot)
    )

    print(
        "🏛️ VEYL ServerInfo activé."
    )