# ============================================================
# VEYL SECURITY CENTER
# Server protection / moderation / security logs
#
# Loaded automatically by bot.py
# ============================================================

import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIG
# ============================================================

SECURITY_LOG_CHANNEL_ID = 1544281215979233280
SECURITY_ENABLED = True

SPAM_WINDOW = 8
SPAM_MESSAGE_LIMIT = 6

MAX_MENTIONS = 8
DUPLICATE_MESSAGE_LIMIT = 4

SUSPICIOUS_DOMAINS = {
    "discord-gift",
    "free-nitro",
    "claim-reward",
    "airdrop-reward",
    "wallet-connect",
    "wallet-verify",
    "metamask-verify",
    "phantom-verify",
}

# ============================================================
# STATE
# ============================================================

message_history = defaultdict(lambda: deque(maxlen=20))
duplicate_history = defaultdict(lambda: deque(maxlen=10))


# ============================================================
# HELPERS
# ============================================================

def is_moderator(member: discord.Member) -> bool:
    if not member:
        return False

    permissions = member.guild_permissions

    return (
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_messages
    )


def get_log_channel(guild: discord.Guild):
    if SECURITY_LOG_CHANNEL_ID:
        channel = guild.get_channel(SECURITY_LOG_CHANNEL_ID)

        if isinstance(channel, discord.TextChannel):
            return channel

    return None


def suspicious_link(content: str) -> bool:
    content = content.lower()

    if "http://" not in content and "https://" not in content:
        return False

    return any(
        keyword in content
        for keyword in SUSPICIOUS_DOMAINS
    )


def build_security_embed(
    title: str,
    description: str,
    guild: discord.Guild,
    user: discord.abc.User | None = None,
):
    embed = discord.Embed(
        title=f"🛡️ VEYL / SECURITY",
        description=description,
        color=0x18191C,
        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(
        name="EVENT",
        value=title,
        inline=True,
    )

    if user:
        embed.add_field(
            name="USER",
            value=f"{user.mention}\n`{user.id}`",
            inline=True,
        )

    embed.set_footer(
        text="VEYL • SECURITY CENTER"
    )

    return embed


async def send_security_log(
    guild: discord.Guild,
    embed: discord.Embed,
):
    channel = get_log_channel(guild)

    if not channel:
        return

    try:
        await channel.send(
            embed=embed
        )
    except discord.HTTPException as error:
        print(
            f"[VEYL SECURITY] Log error: {error}"
        )


# ============================================================
# COG
# ============================================================

class Security(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        print(
            "   ✓ VEYL Security Center activated."
        )

    # ========================================================
    # /security
    # ========================================================

    security_group = app_commands.Group(
        name="security",
        description="VEYL server security controls."
    )

    @security_group.command(
        name="status",
        description="Display the VEYL Security Center status."
    )
    async def security_status(
        self,
        interaction: discord.Interaction,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not is_moderator(interaction.user):
            await interaction.response.send_message(
                "❌ You need moderation permissions.",
                ephemeral=True,
            )
            return

        log_channel = get_log_channel(
            interaction.guild
        )

        embed = discord.Embed(
            title="🛡️ VEYL / SECURITY CENTER",
            description=(
                "Server protection systems."
            ),
            color=0x18191C,
        )

        embed.add_field(
            name="SYSTEM",
            value=(
                "🟢 **ONLINE**"
                if SECURITY_ENABLED
                else "🔴 **DISABLED**"
            ),
            inline=True,
        )

        embed.add_field(
            name="ANTI-SPAM",
            value="🟢 ACTIVE",
            inline=True,
        )

        embed.add_field(
            name="LINK DETECTION",
            value="🟢 ACTIVE",
            inline=True,
        )

        embed.add_field(
            name="MENTION PROTECTION",
            value="🟢 ACTIVE",
            inline=True,
        )

        embed.add_field(
            name="LOG CHANNEL",
            value=(
                log_channel.mention
                if log_channel
                else "⚪ NOT CONFIGURED"
            ),
            inline=True,
        )

        embed.set_footer(
            text="VEYL • SECURITY CENTER"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ):
        if not SECURITY_ENABLED:
            return

        if message.author.bot:
            return

        if not message.guild:
            return

        content = message.content.strip()

        if not content:
            return

        now = time.monotonic()

        key = (
            message.guild.id,
            message.author.id,
        )

        history = message_history[key]

        history.append(now)

        # ----------------------------------------------------
        # Mention protection
        # ----------------------------------------------------

        mention_count = (
            len(message.mentions)
            + len(message.role_mentions)
        )

        if mention_count >= MAX_MENTIONS:

            embed = build_security_embed(
                "MASS MENTION DETECTED",
                (
                    f"Message contains "
                    f"**{mention_count} mentions**.\n"
                    f"Channel: {message.channel.mention}"
                ),
                message.guild,
                message.author,
            )

            await send_security_log(
                message.guild,
                embed,
            )

        # ----------------------------------------------------
        # Suspicious link
        # ----------------------------------------------------

        if suspicious_link(content):

            embed = build_security_embed(
                "SUSPICIOUS LINK DETECTED",
                (
                    f"Potentially suspicious link detected.\n"
                    f"Channel: {message.channel.mention}\n"
                    f"Message ID: `{message.id}`"
                ),
                message.guild,
                message.author,
            )

            await send_security_log(
                message.guild,
                embed,
            )

        # ----------------------------------------------------
        # Spam detection
        # ----------------------------------------------------

        recent = [
            timestamp
            for timestamp in history
            if now - timestamp <= SPAM_WINDOW
        ]

        if len(recent) >= SPAM_MESSAGE_LIMIT:

            embed = build_security_embed(
                "SPAM ACTIVITY DETECTED",
                (
                    f"**{len(recent)} messages** detected "
                    f"within `{SPAM_WINDOW}s`.\n"
                    f"Channel: {message.channel.mention}"
                ),
                message.guild,
                message.author,
            )

            await send_security_log(
                message.guild,
                embed,
            )

            history.clear()

        # ----------------------------------------------------
        # Duplicate detection
        # ----------------------------------------------------

        duplicate_key = (
            message.guild.id,
            message.author.id,
        )

        duplicates = duplicate_history[
            duplicate_key
        ]

        normalized = " ".join(
            content.lower().split()
        )

        duplicates.append(normalized)

        same_count = sum(
            1
            for item in duplicates
            if item == normalized
        )

        if (
            len(normalized) >= 5
            and same_count >= DUPLICATE_MESSAGE_LIMIT
        ):

            embed = build_security_embed(
                "REPEATED MESSAGE DETECTED",
                (
                    f"Repeated message activity detected.\n"
                    f"Channel: {message.channel.mention}"
                ),
                message.guild,
                message.author,
            )

            await send_security_log(
                message.guild,
                embed,
            )

            duplicates.clear()

    # ========================================================
    # MEMBER JOIN
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ):
        embed = build_security_embed(
            "MEMBER JOINED",
            (
                f"{member.mention} joined the server.\n"
                f"Account created: "
                f"<t:{int(member.created_at.timestamp())}:R>"
            ),
            member.guild,
            member,
        )

        await send_security_log(
            member.guild,
            embed,
        )

    # ========================================================
    # MEMBER LEAVE
    # ========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member,
    ):
        embed = build_security_embed(
            "MEMBER LEFT",
            (
                f"**{member}** left the server.\n"
                f"User ID: `{member.id}`"
            ),
            member.guild,
            member,
        )

        await send_security_log(
            member.guild,
            embed,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Security(bot)
    )