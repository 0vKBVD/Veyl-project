import time
import random

import discord
from discord import app_commands
from discord.ext import commands

from services.user_data import (
    get_user,
    add_xp,
    calculate_level,
    get_level_progress,
)


# ============================================================
# VEYL / XP ENGINE
# ============================================================

VEYL_WHITE = 0xF2F2F2
VEYL_GREY = 0x8A8A8A


# ============================================================
# CONFIGURATION
# ============================================================

XP_MIN = 5
XP_MAX = 12

# Un utilisateur peut gagner de l'XP
# une fois toutes les 60 secondes.
XP_COOLDOWN = 60


# ============================================================
# MEMORY
# ============================================================

xp_cooldowns = {}


# ============================================================
# PROGRESS BAR
# ============================================================

def progress_bar(
    percentage,
    length=16
):

    percentage = max(
        0,
        min(
            100,
            percentage
        )
    )

    filled = round(
        percentage / 100 * length
    )

    return (
        "█" * filled
        + "░" * (length - filled)
    )


# ============================================================
# XP REWARD
# ============================================================

def generate_xp():

    return random.randint(
        XP_MIN,
        XP_MAX
    )


# ============================================================
# VEYL XP COG
# ============================================================

class VeylXP(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "⚡ VEYL XP Engine activé."
        )

    # ========================================================
    # /XP
    # ========================================================

    @app_commands.command(
        name="xp",
        description="View your VEYL XP progression."
    )
    @app_commands.describe(
        member="Member whose XP you want to view."
    )
    async def xp(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ):

        target = (
            member
            if member
            else interaction.user
        )

        # ----------------------------------------------------
        # USER DATA
        # ----------------------------------------------------

        user = get_user(
            target.id
        )

        xp = user.get(
            "xp",
            0
        )

        level = calculate_level(
            xp
        )

        progress = get_level_progress(
            xp
        )

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="◈ VEYL / XP",
            description=(
                f"## {target.display_name}\n"
                f"`{target.name}`\n\n"
                f"VEYL COMMUNITY PROGRESSION"
            ),
            color=VEYL_WHITE
        )

        embed.set_thumbnail(
            url=target.display_avatar.url
        )

        # ----------------------------------------------------
        # LEVEL
        # ----------------------------------------------------

        embed.add_field(
            name="LEVEL",
            value=(
                f"**LEVEL {level:02d}**"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # XP
        # ----------------------------------------------------

        embed.add_field(
            name="TOTAL XP",
            value=(
                f"**{xp:,} XP**"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        embed.add_field(
            name="PROGRESS",
            value=(
                f"`{progress_bar(progress['percentage'])}`\n"
                f"**{progress['percentage']:.1f}%**\n"
                f"{progress['remaining']:,} XP remaining"
            ),
            inline=False
        )

        # ----------------------------------------------------
        # XP SYSTEM
        # ----------------------------------------------------

        embed.add_field(
            name="XP SYSTEM",
            value=(
                f"Messages reward **{XP_MIN}–{XP_MAX} XP**.\n"
                f"XP cooldown: **{XP_COOLDOWN}s**."
            ),
            inline=False
        )

        embed.set_footer(
            text=(
                "VEYL XP • COMMUNITY PROGRESSION"
            )
        )

        await interaction.response.send_message(
            embed=embed
        )

    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # ----------------------------------------------------
        # Ignore bots
        # ----------------------------------------------------

        if message.author.bot:
            return

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if message.guild is None:
            return

        user_id = message.author.id

        now = time.time()

        # ----------------------------------------------------
        # COOLDOWN
        # ----------------------------------------------------

        last_xp = xp_cooldowns.get(
            user_id,
            0
        )

        if (
            now - last_xp
            < XP_COOLDOWN
        ):
            return

        # ----------------------------------------------------
        # Update cooldown
        # ----------------------------------------------------

        xp_cooldowns[
            user_id
        ] = now

        # ----------------------------------------------------
        # Generate XP
        # ----------------------------------------------------

        amount = generate_xp()

        # ----------------------------------------------------
        # Add XP
        # ----------------------------------------------------

        try:

            result = add_xp(
                user_id,
                amount
            )

        except Exception as error:

            print(
                f"⚠️ VEYL XP error: "
                f"{type(error).__name__}: {error}"
            )

            return

        # ----------------------------------------------------
        # No result
        # ----------------------------------------------------

        if not result:
            return

        # ----------------------------------------------------
        # LEVEL INFORMATION
        # ----------------------------------------------------

        old_level = result.get(
            "old_level"
        )

        new_level = result.get(
            "new_level"
        )

        if (
            old_level is None
            or new_level is None
        ):
            return

        # ----------------------------------------------------
        # No level up
        # ----------------------------------------------------

        if new_level <= old_level:
            return

        # ====================================================
        # LEVEL UP
        # ====================================================

        embed = discord.Embed(
            title="◈ VEYL / LEVEL UP",
            description=(
                f"## {message.author.display_name}\n\n"
                f"**LEVEL {new_level:02d}**\n\n"
                f"VEYL progression increased.\n"
                f"`+{amount} XP`"
            ),
            color=VEYL_WHITE
        )

        embed.set_thumbnail(
            url=message.author.display_avatar.url
        )

        embed.add_field(
            name="NEW LEVEL",
            value=(
                f"**LEVEL {new_level:02d}**"
            ),
            inline=True
        )

        embed.add_field(
            name="XP EARNED",
            value=(
                f"**+{amount} XP**"
            ),
            inline=True
        )

        embed.set_footer(
            text=(
                "VEYL XP • LEVEL PROGRESSION"
            )
        )

        try:

            await message.channel.send(
                embed=embed
            )

        except discord.Forbidden:

            pass

        except discord.HTTPException:

            pass


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        VeylXP(bot)
    )
