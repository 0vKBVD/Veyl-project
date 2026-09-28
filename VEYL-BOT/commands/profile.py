import discord
from discord import app_commands
from discord.ext import commands

from services.user_data import (
    get_user,
    calculate_level,
    get_level_progress,
    get_user_rank,
)


# ============================================================
# VEYL / PROFILE
# ============================================================

VEYL_WHITE = 0xF2F2F2


# ============================================================
# BADGES
# ============================================================

BADGE_NAMES = {
    "early_member": "◈ EARLY MEMBER",
    "market_watcher": "◈ MARKET WATCHER",
    "cascade_hunter": "◈ CASCADE HUNTER",
    "terminal_user": "◈ TERMINAL USER",
    "veyl_core": "◈ VEYL CORE",
}


# ============================================================
# PROGRESS BAR
# ============================================================

def progress_bar(
    percentage,
    length=14
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
# PROFILE COG
# ============================================================

class VeylProfile(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "👤 VEYL Profile Engine activé."
        )

    # ========================================================
    # /PROFILE
    # ========================================================

    @app_commands.command(
        name="profile",
        description="View a VEYL member profile."
    )
    @app_commands.describe(
        member="Member whose profile you want to view."
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None
    ):

        target = (
            member
            if member
            else interaction.user
        )

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

        rank = get_user_rank(
            target.id
        )

        # ----------------------------------------------------
        # BADGES
        # ----------------------------------------------------

        badges = user.get(
            "badges",
            []
        )

        if badges:

            badge_text = "\n".join(
                BADGE_NAMES.get(
                    badge,
                    f"◈ {badge.upper()}"
                )
                for badge in badges
            )

        else:

            badge_text = (
                "`NO BADGES YET`"
            )

        # ----------------------------------------------------
        # WATCHLIST
        # ----------------------------------------------------

        watchlist = user.get(
            "watchlist",
            []
        )

        # ----------------------------------------------------
        # MEMBER SINCE
        # ----------------------------------------------------

        member_since = "UNKNOWN"

        created_at = user.get(
            "created_at"
        )

        if created_at:

            try:

                dt = discord.utils.parse_time(
                    created_at
                )

                if dt:

                    member_since = (
                        discord.utils.format_dt(
                            dt,
                            style="D"
                        )
                    )

            except Exception:

                member_since = "UNKNOWN"

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="◈ VEYL / PROFILE",
            description=(
                f"## {target.display_name}\n"
                f"`{target.name}`\n\n"
                f"VEYL MEMBER PROFILE"
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
            name="VEYL LEVEL",
            value=(
                f"**LEVEL {level:02d}**\n"
                f"`{progress_bar(progress['percentage'])}`\n"
                f"**{xp:,} XP**"
            ),
            inline=False
        )

        # ----------------------------------------------------
        # RANK
        # ----------------------------------------------------

        embed.add_field(
            name="RANK",
            value=(
                f"**#{rank if rank else '—'}**\n"
                f"Global VEYL ranking"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # COMMANDS
        # ----------------------------------------------------

        embed.add_field(
            name="COMMANDS",
            value=(
                f"**{user.get('commands_used', 0):,}**\n"
                f"commands used"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # WATCHLIST
        # ----------------------------------------------------

        embed.add_field(
            name="WATCHLIST",
            value=(
                f"**{len(watchlist)}**\n"
                f"assets tracked"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # BADGES
        # ----------------------------------------------------

        embed.add_field(
            name="BADGES",
            value=badge_text,
            inline=False
        )

        # ----------------------------------------------------
        # MEMBER SINCE
        # ----------------------------------------------------

        embed.add_field(
            name="MEMBER SINCE",
            value=member_since,
            inline=True
        )

        # ----------------------------------------------------
        # NEXT LEVEL
        # ----------------------------------------------------

        embed.add_field(
            name="NEXT LEVEL",
            value=(
                f"**{progress['remaining']:,} XP**\n"
                f"remaining"
            ),
            inline=True
        )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        embed.set_footer(
            text=(
                "VEYL PROFILE • "
                "MARKET INTELLIGENCE COMMUNITY"
            )
        )

        await interaction.response.send_message(
            embed=embed
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        VeylProfile(bot)
    )