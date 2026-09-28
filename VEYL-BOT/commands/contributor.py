# ============================================================
# VEYL CONTRIBUTOR SYSTEM
# Community contribution tracking
# ============================================================

import json
import os
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIG
# ============================================================

DATA_FOLDER = "data"
DATA_FILE = os.path.join(
    DATA_FOLDER,
    "contributors.json",
)

CONTRIBUTOR_ROLE_ID = 1544281777630085170
CONTRIBUTOR_ADMIN_ROLE_ID = 0

CONTRIBUTOR_XP_PER_ACTION = 25


# ============================================================
# STORAGE
# ============================================================

def ensure_storage():
    os.makedirs(
        DATA_FOLDER,
        exist_ok=True,
    )

    if not os.path.exists(DATA_FILE):
        with open(
            DATA_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                {},
                file,
                indent=4,
            )


def load_data():
    ensure_storage()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_data(data):
    ensure_storage()

    temporary = DATA_FILE + ".tmp"

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=4,
        )

    os.replace(
        temporary,
        DATA_FILE,
    )


# ============================================================
# HELPERS
# ============================================================

def is_admin(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_guild:
        return True

    if (
        CONTRIBUTOR_ADMIN_ROLE_ID
        and any(
            role.id == CONTRIBUTOR_ADMIN_ROLE_ID
            for role in member.roles
        )
    ):
        return True

    return False


def contributor_entry(
    data,
    guild_id,
    user_id,
):
    guild = data.setdefault(
        str(guild_id),
        {}
    )

    return guild.setdefault(
        str(user_id),
        {
            "xp": 0,
            "contributions": 0,
            "badges": [],
        }
    )


def contributor_level(xp):
    return max(
        1,
        int(xp // 250) + 1,
    )


def badge_for_count(count):
    if count >= 100:
        return "🏆 LEGEND"

    if count >= 50:
        return "💎 ELITE CONTRIBUTOR"

    if count >= 25:
        return "⚡ CORE CONTRIBUTOR"

    if count >= 10:
        return "🔎 CONTRIBUTOR"

    return None


# ============================================================
# COG
# ============================================================

class Contributor(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        print(
            "   ✓ VEYL Contributor System activated."
        )

    # ========================================================
    # GROUP
    # ========================================================

    contributor_group = app_commands.Group(
        name="contributor",
        description="VEYL community contributor system."
    )

    # ========================================================
    # /contributor profile
    # ========================================================

    @contributor_group.command(
        name="profile",
        description="View a contributor profile."
    )
    @app_commands.describe(
        member="Member to inspect"
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        member = member or interaction.user

        data = load_data()

        entry = contributor_entry(
            data,
            interaction.guild.id,
            member.id,
        )

        xp = int(entry["xp"])
        contributions = int(
            entry["contributions"]
        )

        level = contributor_level(xp)

        badges = entry.get(
            "badges",
            []
        )

        embed = discord.Embed(
            title="🏆 VEYL / CONTRIBUTOR",
            description=(
                f"**{member.display_name}**\n"
                f"{member.mention}"
            ),
            color=0x18191C,
        )

        embed.add_field(
            name="LEVEL",
            value=f"**{level}**",
            inline=True,
        )

        embed.add_field(
            name="XP",
            value=f"**{xp:,}**",
            inline=True,
        )

        embed.add_field(
            name="CONTRIBUTIONS",
            value=f"**{contributions}**",
            inline=True,
        )

        embed.add_field(
            name="BADGES",
            value=(
                "\n".join(badges)
                if badges
                else "No badges yet."
            ),
            inline=False,
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.set_footer(
            text="VEYL • CONTRIBUTOR SYSTEM"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # /contributor add
    # ========================================================

    @contributor_group.command(
        name="add",
        description="Register a contribution."
    )
    @app_commands.describe(
        member="Contributor",
        amount="Contribution amount"
    )
    async def add_contribution(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int = 1,
    ):
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need server management permissions.",
                ephemeral=True,
            )
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "❌ Amount must be between 1 and 100.",
                ephemeral=True,
            )
            return

        data = load_data()

        entry = contributor_entry(
            data,
            interaction.guild.id,
            member.id,
        )

        old_level = contributor_level(
            int(entry["xp"])
        )

        entry["contributions"] += amount
        entry["xp"] += (
            CONTRIBUTOR_XP_PER_ACTION
            * amount
        )

        badge = badge_for_count(
            int(entry["contributions"])
        )

        if badge and badge not in entry["badges"]:
            entry["badges"].append(
                badge
            )

        save_data(data)

        new_level = contributor_level(
            int(entry["xp"])
        )

        # ----------------------------------------------------
        # Role
        # ----------------------------------------------------

        role = None

        if CONTRIBUTOR_ROLE_ID:
            role = interaction.guild.get_role(
                CONTRIBUTOR_ROLE_ID
            )

        if role and role not in member.roles:
            try:
                await member.add_roles(
                    role,
                    reason="VEYL Contributor System",
                )
            except discord.HTTPException:
                pass

        embed = discord.Embed(
            title="🏆 CONTRIBUTION REGISTERED",
            description=(
                f"{member.mention} received "
                f"**{amount} contribution(s)**."
            ),
            color=0x18191C,
        )

        embed.add_field(
            name="XP",
            value=f"+{CONTRIBUTOR_XP_PER_ACTION * amount}",
            inline=True,
        )

        embed.add_field(
            name="TOTAL",
            value=f"{entry['contributions']}",
            inline=True,
        )

        if new_level > old_level:
            embed.add_field(
                name="LEVEL UP",
                value=f"⭐ Level **{new_level}**",
                inline=True,
            )

        await interaction.response.send_message(
            embed=embed,
        )

    # ========================================================
    # /contributors
    # ========================================================

    @app_commands.command(
        name="contributors",
        description="Show the VEYL contributor leaderboard."
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
    ):
        if not interaction.guild:
            return

        data = load_data()

        guild_data = data.get(
            str(interaction.guild.id),
            {}
        )

        ranking = []

        for user_id, entry in guild_data.items():
            try:
                ranking.append(
                    (
                        int(user_id),
                        int(entry.get("contributions", 0)),
                        int(entry.get("xp", 0)),
                    )
                )
            except Exception:
                continue

        ranking.sort(
            key=lambda item: (
                item[1],
                item[2],
            ),
            reverse=True,
        )

        lines = []

        for index, (
            user_id,
            contributions,
            xp,
        ) in enumerate(
            ranking[:10],
            start=1,
        ):

            member = interaction.guild.get_member(
                user_id
            )

            name = (
                member.display_name
                if member
                else f"User {user_id}"
            )

            lines.append(
                f"**{index}.** {name} "
                f"— `{contributions}` contributions "
                f"• `{xp:,}` XP"
            )

        if not lines:
            lines.append(
                "No contributors registered yet."
            )

        embed = discord.Embed(
            title="🏆 VEYL / CONTRIBUTOR LEADERBOARD",
            description="\n".join(lines),
            color=0x18191C,
        )

        embed.set_footer(
            text="VEYL • COMMUNITY CONTRIBUTORS"
        )

        await interaction.response.send_message(
            embed=embed,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Contributor(bot)
    )