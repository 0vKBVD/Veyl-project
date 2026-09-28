# ============================================================
# VEYL RECAP ENGINE
# Daily / weekly server statistics
# ============================================================

import asyncio
import json
import os
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# CONFIG
# ============================================================

DATA_FOLDER = "data"
DATA_FILE = os.path.join(
    DATA_FOLDER,
    "recap.json",
)

RECAP_CHANNEL_ID = 0

AUTO_DAILY_RECAP = False
AUTO_WEEKLY_RECAP = False

DAILY_INTERVAL_SECONDS = 86400
WEEKLY_INTERVAL_SECONDS = 604800


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

def guild_entry(
    data,
    guild_id,
):

    return data.setdefault(
        str(guild_id),
        {
            "messages": 0,
            "commands": 0,
            "joins": 0,
            "leaves": 0,
            "scans": 0,
            "alerts": 0,
            "started_at": time.time(),
        },
    )


def get_recap_channel(
    guild: discord.Guild,
):

    if not RECAP_CHANNEL_ID:
        return None

    channel = guild.get_channel(
        RECAP_CHANNEL_ID
    )

    if isinstance(
        channel,
        discord.TextChannel,
    ):
        return channel

    return None


def format_uptime(seconds):

    seconds = int(seconds)

    days, seconds = divmod(
        seconds,
        86400,
    )

    hours, seconds = divmod(
        seconds,
        3600,
    )

    minutes, _ = divmod(
        seconds,
        60,
    )

    parts = []

    if days:
        parts.append(
            f"{days}d"
        )

    if hours:
        parts.append(
            f"{hours}h"
        )

    if minutes:
        parts.append(
            f"{minutes}m"
        )

    return " ".join(
        parts
    ) or "0m"


# ============================================================
# COG
# ============================================================

class Recap(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.daily_task.start()
        self.weekly_task.start()

        print(
            "   ✓ VEYL Recap Engine activated."
        )

    def cog_unload(self):

        self.daily_task.cancel()
        self.weekly_task.cancel()

    # ========================================================
    # RECORD MESSAGE
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ):

        if message.author.bot:
            return

        if not message.guild:
            return

        data = load_data()

        entry = guild_entry(
            data,
            message.guild.id,
        )

        entry["messages"] += 1

        save_data(data)

    # ========================================================
    # MEMBER JOIN
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ):

        data = load_data()

        entry = guild_entry(
            data,
            member.guild.id,
        )

        entry["joins"] += 1

        save_data(data)

    # ========================================================
    # MEMBER LEAVE
    # ========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member,
    ):

        data = load_data()

        entry = guild_entry(
            data,
            member.guild.id,
        )

        entry["leaves"] += 1

        save_data(data)

    # ========================================================
    # COMMAND
    # ========================================================

    @app_commands.command(
        name="recap",
        description="Generate the VEYL server recap."
    )
    async def recap(
        self,
        interaction: discord.Interaction,
    ):

        if not interaction.guild:

            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )

            return

        await interaction.response.defer()

        data = load_data()

        entry = guild_entry(
            data,
            interaction.guild.id,
        )

        started_at = float(
            entry.get(
                "started_at",
                time.time(),
            )
        )

        uptime = (
            time.time()
            - started_at
        )

        # ----------------------------------------------------
        # Active members
        # ----------------------------------------------------

        active_members = sum(
            1
            for member in interaction.guild.members
            if not member.bot
        )

        # ----------------------------------------------------
        # Channels
        # ----------------------------------------------------

        text_channels = sum(
            1
            for channel in interaction.guild.channels
            if isinstance(
                channel,
                discord.TextChannel,
            )
        )

        voice_channels = sum(
            1
            for channel in interaction.guild.channels
            if isinstance(
                channel,
                discord.VoiceChannel,
            )
        )

        # ----------------------------------------------------
        # Embed
        # ----------------------------------------------------

        now = datetime.now(
            timezone.utc
        )

        embed = discord.Embed(
            title="📊 VEYL / SERVER RECAP",
            description=(
                f"**{interaction.guild.name}**\n"
                f"Generated <t:{int(now.timestamp())}:R>"
            ),
            color=0x18191C,
        )

        embed.add_field(
            name="COMMUNITY",
            value=(
                f"MEMBERS  **{interaction.guild.member_count:,}**\n"
                f"ACTIVE   **{active_members:,}**\n"
                f"JOINS    **{entry['joins']:,}**\n"
                f"LEAVES   **{entry['leaves']:,}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="ACTIVITY",
            value=(
                f"MESSAGES **{entry['messages']:,}**\n"
                f"COMMANDS **{entry['commands']:,}**\n"
                f"SCANS    **{entry['scans']:,}**\n"
                f"ALERTS   **{entry['alerts']:,}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="SERVER",
            value=(
                f"TEXT     **{text_channels}**\n"
                f"VOICE    **{voice_channels}**\n"
                f"UPTIME   **{format_uptime(uptime)}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="VEYL SYSTEM",
            value=(
                "🟢 Core\n"
                "🟢 Command System\n"
                "🟢 Recap Engine"
            ),
            inline=False,
        )

        embed.set_footer(
            text="VEYL • MARKET INTELLIGENCE"
        )

        await interaction.followup.send(
            embed=embed
        )

    # ========================================================
    # DAILY
    # ========================================================

    @tasks.loop(seconds=DAILY_INTERVAL_SECONDS)
    async def daily_task(self):

        if not AUTO_DAILY_RECAP:
            return

        for guild in self.bot.guilds:

            channel = get_recap_channel(
                guild
            )

            if not channel:
                continue

            try:

                await self.send_recap(
                    guild,
                    channel,
                    "DAILY RECAP",
                )

            except Exception as error:

                print(
                    "[VEYL RECAP] Daily error:",
                    type(error).__name__,
                    error,
                )

    # ========================================================
    # WEEKLY
    # ========================================================

    @tasks.loop(seconds=WEEKLY_INTERVAL_SECONDS)
    async def weekly_task(self):

        if not AUTO_WEEKLY_RECAP:
            return

        for guild in self.bot.guilds:

            channel = get_recap_channel(
                guild
            )

            if not channel:
                continue

            try:

                await self.send_recap(
                    guild,
                    channel,
                    "WEEKLY RECAP",
                )

            except Exception as error:

                print(
                    "[VEYL RECAP] Weekly error:",
                    type(error).__name__,
                    error,
                )

    # ========================================================
    # SEND RECAP
    # ========================================================

    async def send_recap(
        self,
        guild,
        channel,
        title,
    ):

        data = load_data()

        entry = guild_entry(
            data,
            guild.id,
        )

        embed = discord.Embed(
            title=f"📊 VEYL / {title}",
            description=(
                f"**{guild.name}**\n"
                "Community & system activity overview."
            ),
            color=0x18191C,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="COMMUNITY",
            value=(
                f"Members **{guild.member_count:,}**\n"
                f"Joins **{entry['joins']:,}**\n"
                f"Leaves **{entry['leaves']:,}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="ACTIVITY",
            value=(
                f"Messages **{entry['messages']:,}**\n"
                f"Commands **{entry['commands']:,}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="VEYL",
            value=(
                f"Scans **{entry['scans']:,}**\n"
                f"Alerts **{entry['alerts']:,}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="SYSTEM",
            value="🟢 VEYL CORE ONLINE",
            inline=False,
        )

        embed.set_footer(
            text="VEYL • AUTOMATED RECAP"
        )

        await channel.send(
            embed=embed
        )

    # ========================================================
    # TASK READY
    # ========================================================

    @daily_task.before_loop
    async def before_daily(
        self,
    ):

        await self.bot.wait_until_ready()

    @weekly_task.before_loop
    async def before_weekly(
        self,
    ):

        await self.bot.wait_until_ready()


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Recap(bot)
    )