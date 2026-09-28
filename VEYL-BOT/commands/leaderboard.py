import json
import os
import random
import time

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = "leaderboard.json"

XP_MIN = 5
XP_MAX = 15

XP_COOLDOWN = 60  # 1 XP gain par minute maximum


# ============================================================
# DATA
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"⚠️ Impossible de charger le leaderboard : {error}"
        )

        return {}


def save_data(data):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    except Exception as error:

        print(
            f"❌ Impossible de sauvegarder le leaderboard : {error}"
        )


# ============================================================
# VEYL LEADERBOARD
# ============================================================

class VeylLeaderboard(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.data = load_data()

        self.cooldowns = {}

    # ========================================================
    # ADD XP
    # ========================================================

    def add_xp(
        self,
        user_id
    ):

        user_id = str(
            user_id
        )

        if user_id not in self.data:

            self.data[user_id] = {
                "xp": 0,
                "level": 1
            }

        gained_xp = random.randint(
            XP_MIN,
            XP_MAX
        )

        self.data[user_id]["xp"] += gained_xp

        # Niveau
        xp = self.data[user_id]["xp"]

        level = 1

        while xp >= self.xp_required(level + 1):

            level += 1

        self.data[user_id]["level"] = level

        save_data(
            self.data
        )

        return gained_xp

    # ========================================================
    # XP REQUIRED
    # ========================================================

    def xp_required(
        self,
        level
    ):

        return (
            100
            * (level - 1)
            * (level - 1)
            + 100
        )

    # ========================================================
    # MESSAGE XP
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        # Ignore bots
        if message.author.bot:
            return

        user_id = message.author.id

        now = time.time()

        # Cooldown
        last_xp = self.cooldowns.get(
            user_id,
            0
        )

        if now - last_xp < XP_COOLDOWN:
            return

        self.cooldowns[user_id] = now

        self.add_xp(
            user_id
        )

    # ========================================================
    # /LEADERBOARD
    # ========================================================

    @app_commands.command(
        name="leaderboard",
        description="View the VEYL community leaderboard."
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction
    ):

        if not self.data:

            await interaction.response.send_message(
                "🏆 The VEYL leaderboard is currently empty.",
                ephemeral=True
            )

            return

        sorted_users = sorted(
            self.data.items(),
            key=lambda item: item[1].get(
                "xp",
                0
            ),
            reverse=True
        )

        embed = discord.Embed(
            title="🏆 VEYL LEADERBOARD",
            description=(
                "The most active members of the VEYL community."
            ),
            color=discord.Color.blurple()
        )

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        lines = []

        for position, (
            user_id,
            stats
        ) in enumerate(
            sorted_users[:10],
            start=1
        ):

            try:

                user = self.bot.get_user(
                    int(user_id)
                )

                if user is None:

                    user = await self.bot.fetch_user(
                        int(user_id)
                    )

                username = user.display_name

            except Exception:

                username = "Unknown Member"

            xp = stats.get(
                "xp",
                0
            )

            level = stats.get(
                "level",
                1
            )

            if position <= 3:

                rank = medals[
                    position - 1
                ]

            else:

                rank = f"`#{position}`"

            lines.append(
                f"{rank} **{username}**\n"
                f"　Level **{level}** · **{xp:,} XP**"
            )

        embed.description += (
            "\n\n"
            + "\n\n".join(lines)
        )

        embed.set_footer(
            text="VEYL • Community Leaderboard"
        )

        await interaction.response.send_message(
            embed=embed
        )

    # ========================================================
    # /RANK
    # ========================================================

    @app_commands.command(
        name="rank",
        description="View your VEYL rank."
    )
    async def rank(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(
            interaction.user.id
        )

        if user_id not in self.data:

            self.data[user_id] = {
                "xp": 0,
                "level": 1
            }

            save_data(
                self.data
            )

        sorted_users = sorted(
            self.data.items(),
            key=lambda item: item[1].get(
                "xp",
                0
            ),
            reverse=True
        )

        position = next(
            (
                i + 1
                for i, item in enumerate(
                    sorted_users
                )
                if item[0] == user_id
            ),
            len(sorted_users)
        )

        stats = self.data[user_id]

        xp = stats.get(
            "xp",
            0
        )

        level = stats.get(
            "level",
            1
        )

        embed = discord.Embed(
            title="🏆 YOUR VEYL RANK",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="RANK",
            value=f"**#{position}**",
            inline=True
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

        embed.set_footer(
            text="VEYL • Community"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylLeaderboard(bot)
    )

    print(
        "🏆 VEYL Leaderboard activé."
    )