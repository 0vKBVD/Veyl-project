import discord
from discord.ext import commands


# ============================================================
# VEYL — JOIN LOG
# ============================================================

JOIN_LOG_CHANNEL_ID = 1542891891471810601


# ============================================================
# VEYL JOIN LOG COG
# ============================================================

class VeylJoinLog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        print("👋 VEYL Join Log activé.")
        print(
            f"   └─ Channel ID : {JOIN_LOG_CHANNEL_ID}"
        )

    # ========================================================
    # MEMBER JOIN
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        channel = self.bot.get_channel(
            JOIN_LOG_CHANNEL_ID
        )

        if channel is None:

            print(
                "⚠️ VEYL Join Log : "
                "salon introuvable."
            )

            return

        account_created = int(
            member.created_at.timestamp()
        )

        embed = discord.Embed(
            title="✦ VEYL // NEW MEMBER",
            description=(
                "```text\n"
                "╔══════════════════════════════════════╗\n"
                "║          VEYL ACCESS SYSTEM          ║\n"
                "║             NEW MEMBER               ║\n"
                "╚══════════════════════════════════════╝\n"
                "```\n"
                f"Welcome to **VEYL**, "
                f"{member.mention}.\n\n"
                f"**USER**\n"
                f"`{member}`\n\n"
                f"**ACCOUNT CREATED**\n"
                f"<t:{account_created}:F>\n\n"
                f"**MEMBER COUNT**\n"
                f"`{member.guild.member_count}`"
            ),
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        if member.avatar:

            embed.set_thumbnail(
                url=member.avatar.url
            )

        embed.set_footer(
            text=(
                "VEYL • MEMBER SYSTEM • JOIN LOG"
            )
        )

        try:

            await channel.send(
                embed=embed
            )

            print(
                f"👋 Join Log : "
                f"{member} rejoint le serveur."
            )

        except discord.HTTPException as error:

            print(
                f"❌ Join Log Discord error : "
                f"{error}"
            )

    # ========================================================
    # MEMBER LEAVE
    # ========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member
    ):

        channel = self.bot.get_channel(
            JOIN_LOG_CHANNEL_ID
        )

        if channel is None:

            print(
                "⚠️ VEYL Join Log : "
                "salon introuvable."
            )

            return

        embed = discord.Embed(
            title="✦ VEYL // MEMBER LEFT",
            description=(
                "```text\n"
                "╔══════════════════════════════════════╗\n"
                "║          VEYL ACCESS SYSTEM          ║\n"
                "║             MEMBER LEFT              ║\n"
                "╚══════════════════════════════════════╝\n"
                "```\n"
                f"**USER**\n"
                f"`{member}`\n\n"
                f"**MEMBER COUNT**\n"
                f"`{member.guild.member_count}`"
            ),
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow()
        )

        if member.avatar:

            embed.set_thumbnail(
                url=member.avatar.url
            )

        embed.set_footer(
            text=(
                "VEYL • MEMBER SYSTEM • LEAVE LOG"
            )
        )

        try:

            await channel.send(
                embed=embed
            )

            print(
                f"👋 Join Log : "
                f"{member} a quitté le serveur."
            )

        except discord.HTTPException as error:

            print(
                f"❌ Leave Log Discord error : "
                f"{error}"
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylJoinLog(bot)
    )

    print(
        "   ✅ commands.joinlog"
    )
