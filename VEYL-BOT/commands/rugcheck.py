# ============================================================
# VEYL RUGCHECK
# SOLANA TOKEN RISK INTELLIGENCE
#
# Command:
#   /rugcheck <mint>
#
# Read-only.
# No wallet.
# No private keys.
# No transactions.
# ============================================================

import asyncio
import time
import traceback
from typing import Optional

import aiohttp
import discord

from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

RUGCHECK_API = "https://api.rugcheck.xyz/v1"

REQUEST_TIMEOUT = 7

COMMAND_COOLDOWN = 8

RUGCHECK_CACHE_TTL = 30

EMBED_COLOR = 0x18191C

_cache = {}


# ============================================================
# HELPERS
# ============================================================

def clean(value, fallback="—"):

    if value is None:
        return fallback

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return fallback

        return value

    return value


def shorten(value, length=18):

    value = str(clean(value))

    if len(value) <= length:
        return value

    return value[:length - 3] + "..."


def format_number(value):

    if value is None:
        return "—"

    try:
        number = float(value)

    except (TypeError, ValueError):
        return "—"

    if number >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.2f}T"

    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"

    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"

    if number >= 1_000:
        return f"{number / 1_000:.2f}K"

    return f"{number:,.2f}"


def format_pct(value):

    if value is None:
        return "—"

    try:
        return f"{float(value):.2f}%"

    except (TypeError, ValueError):
        return "—"


def authority_status(value):

    if value is None:
        return "RENOUNCED"

    if isinstance(value, str):

        if not value.strip():
            return "RENOUNCED"

        return "ACTIVE"

    return "ACTIVE"


def authority_address(value):

    if value is None:
        return "None"

    if isinstance(value, str):

        if not value.strip():
            return "None"

        return shorten(value, 20)

    return "ACTIVE"


def risk_emoji(level):

    if not level:
        return "⚪"

    level = str(level).lower()

    if level in (
        "danger",
        "critical",
        "high",
        "error",
    ):
        return "🔴"

    if level in (
        "warning",
        "medium",
        "moderate",
    ):
        return "🟠"

    if level in (
        "good",
        "low",
        "safe",
        "info",
    ):
        return "🟢"

    return "⚪"


def risk_label(level):

    if not level:
        return "UNKNOWN"

    level = str(level).upper()

    mapping = {
        "DANGER": "HIGH",
        "CRITICAL": "CRITICAL",
        "ERROR": "HIGH",
        "WARNING": "MEDIUM",
        "MODERATE": "MEDIUM",
        "GOOD": "LOW",
        "SAFE": "LOW",
        "INFO": "LOW",
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
    }

    return mapping.get(
        level,
        level,
    )


def calculate_verdict(data):

    risk_level = (
        data.get("riskLevel")
        or data.get("risk_level")
    )

    score = data.get("score")

    try:
        score = float(score)

    except (TypeError, ValueError):
        score = None

    if risk_level:

        level = str(
            risk_level
        ).lower()

        if level in (
            "danger",
            "critical",
            "high",
        ):
            return "HIGH RISK"

        if level in (
            "warning",
            "medium",
            "moderate",
        ):
            return "MEDIUM RISK"

        if level in (
            "good",
            "safe",
            "low",
        ):
            return "LOW RISK"

    if score is not None:

        if score >= 150:
            return "LOW RISK"

        if score >= 80:
            return "MEDIUM RISK"

        return "HIGH RISK"

    return "UNKNOWN"


# ============================================================
# API
# ============================================================

async def fetch_rugcheck(
    mint: str,
) -> Optional[dict]:

    mint = mint.strip()

    if not mint:
        return None

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    now = time.monotonic()

    cached = _cache.get(mint)

    if cached:

        cached_time, cached_data = cached

        if (
            now - cached_time
            < RUGCHECK_CACHE_TTL
        ):

            print(
                f"   ✓ RugCheck cache hit: "
                f"{shorten(mint, 18)}"
            )

            return cached_data

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    url = (
        f"{RUGCHECK_API}"
        f"/tokens/{mint}/report"
    )

    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT,
        connect=3,
        sock_connect=3,
        sock_read=5,
    )

    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    headers = {
        "Accept": "application/json",
        "User-Agent": "VEYL-RugCheck/1.0",
    }

    print()
    print("⌘ VEYL / RUGCHECK")
    print(
        f"   Mint: {mint}"
    )
    print(
        "   Connecting to RugCheck API..."
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        ) as session:

            async with session.get(
                url
            ) as response:

                print(
                    f"   HTTP: {response.status}"
                )

                # ------------------------------------------------
                # RATE LIMIT
                # ------------------------------------------------

                if response.status == 429:

                    print(
                        "   ❌ RugCheck rate limit."
                    )

                    return None

                # ------------------------------------------------
                # NOT FOUND
                # ------------------------------------------------

                if response.status == 404:

                    print(
                        "   ❌ Token not found."
                    )

                    return None

                # ------------------------------------------------
                # FORBIDDEN
                # ------------------------------------------------

                if response.status == 403:

                    print(
                        "   ❌ RugCheck returned HTTP 403."
                    )

                    return None

                # ------------------------------------------------
                # SERVER ERROR
                # ------------------------------------------------

                if response.status >= 500:

                    print(
                        "   ❌ RugCheck server error."
                    )

                    return None

                # ------------------------------------------------
                # OTHER ERROR
                # ------------------------------------------------

                if response.status != 200:

                    print(
                        "   ❌ Unexpected RugCheck HTTP "
                        f"status: {response.status}"
                    )

                    return None

                # ------------------------------------------------
                # JSON
                # ------------------------------------------------

                try:

                    data = await response.json(
                        content_type=None
                    )

                except Exception as error:

                    print(
                        "   ❌ RugCheck returned invalid JSON:"
                        f" {error}"
                    )

                    return None

                # ------------------------------------------------
                # VALIDATION
                # ------------------------------------------------

                if not isinstance(
                    data,
                    dict,
                ):

                    print(
                        "   ❌ RugCheck response "
                        "is not an object."
                    )

                    return None

                # ------------------------------------------------
                # CACHE
                # ------------------------------------------------

                _cache[mint] = (
                    time.monotonic(),
                    data,
                )

                print(
                    "   ✓ RugCheck report received."
                )

                return data

    except asyncio.TimeoutError:

        print(
            "   ❌ RugCheck request timed out."
        )

        return None

    except aiohttp.ClientConnectorError as error:

        print(
            "   ❌ Cannot connect to RugCheck:"
            f" {error}"
        )

        return None

    except aiohttp.ClientResponseError as error:

        print(
            "   ❌ RugCheck HTTP error:"
            f" {error}"
        )

        return None

    except aiohttp.ClientError as error:

        print(
            "   ❌ RugCheck network error:"
            f" {error}"
        )

        return None

    except Exception as error:

        print(
            "   ❌ RugCheck unexpected error:"
            f" {type(error).__name__}: {error}"
        )

        traceback.print_exc()

        return None


# ============================================================
# DATA EXTRACTION
# ============================================================

def extract_token_name(data):

    token_meta = data.get(
        "tokenMeta"
    )

    if isinstance(
        token_meta,
        dict,
    ):

        name = token_meta.get(
            "name"
        )

        if name:
            return str(name)

        symbol = token_meta.get(
            "symbol"
        )

        if symbol:
            return str(symbol)

    token = data.get(
        "token"
    )

    if isinstance(
        token,
        dict,
    ):

        name = token.get(
            "name"
        )

        if name:
            return str(name)

        symbol = token.get(
            "symbol"
        )

        if symbol:
            return str(symbol)

    return "Unknown Token"


def extract_symbol(data):

    token_meta = data.get(
        "tokenMeta"
    )

    if isinstance(
        token_meta,
        dict,
    ):

        symbol = token_meta.get(
            "symbol"
        )

        if symbol:
            return str(symbol)

    token = data.get(
        "token"
    )

    if isinstance(
        token,
        dict,
    ):

        symbol = token.get(
            "symbol"
        )

        if symbol:
            return str(symbol)

    return "TOKEN"


def extract_authority(
    data,
    key,
):

    value = data.get(
        key
    )

    if value is not None:
        return value

    token = data.get(
        "token"
    )

    if isinstance(
        token,
        dict,
    ):

        return token.get(
            key
        )

    return None


def extract_top_holders_pct(data):

    value = data.get(
        "topHoldersPct"
    )

    if value is not None:
        return value

    value = data.get(
        "top_holders_pct"
    )

    if value is not None:
        return value

    holders = data.get(
        "topHolders"
    )

    if not isinstance(
        holders,
        list,
    ):
        return None

    total = 0.0

    found = False

    for holder in holders:

        if not isinstance(
            holder,
            dict,
        ):
            continue

        pct = (
            holder.get("pct")
            or holder.get("percentage")
            or holder.get("ownershipPercentage")
        )

        try:

            total += float(pct)
            found = True

        except (
            TypeError,
            ValueError,
        ):
            continue

    if found:
        return total

    return None


def extract_liquidity(data):

    direct = (
        data.get(
            "totalMarketLiquidity"
        )
        or data.get(
            "totalLiquidity"
        )
    )

    if direct is not None:
        return direct

    markets = data.get(
        "markets"
    )

    if not isinstance(
        markets,
        list,
    ):
        return None

    total = 0.0
    found = False

    for market in markets:

        if not isinstance(
            market,
            dict,
        ):
            continue

        value = (
            market.get("lp")
            or market.get("liquidity")
            or market.get("liquidityUsd")
            or market.get("lpLiquidity")
        )

        try:

            total += float(value)
            found = True

        except (
            TypeError,
            ValueError,
        ):
            continue

    if found:
        return total

    return None


def extract_risks(data):

    risks = data.get(
        "risks"
    )

    if not isinstance(
        risks,
        list,
    ):
        return []

    return [
        risk
        for risk in risks
        if isinstance(
            risk,
            dict,
        )
    ]


# ============================================================
# EMBED
# ============================================================

def build_rugcheck_embed(
    data,
    mint,
):

    name = extract_token_name(
        data
    )

    symbol = extract_symbol(
        data
    )

    score = data.get(
        "score"
    )

    risk_level = (
        data.get("riskLevel")
        or data.get("risk_level")
    )

    verdict = calculate_verdict(
        data
    )

    mint_authority = extract_authority(
        data,
        "mintAuthority",
    )

    freeze_authority = extract_authority(
        data,
        "freezeAuthority",
    )

    holders_pct = extract_top_holders_pct(
        data
    )

    liquidity = extract_liquidity(
        data
    )

    risks = extract_risks(
        data
    )

    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = discord.Embed(
        title="⌘ VEYL / RUGCHECK",
        description=(
            f"**{name}** · `{symbol}`\n"
            f"`{shorten(mint, 32)}`"
        ),
        color=EMBED_COLOR,
    )

    # --------------------------------------------------------
    # VERDICT
    # --------------------------------------------------------

    verdict_icon = {
        "LOW RISK": "🟢",
        "MEDIUM RISK": "🟠",
        "HIGH RISK": "🔴",
        "UNKNOWN": "⚪",
    }.get(
        verdict,
        "⚪",
    )

    embed.add_field(
        name="◈ VEYL VERDICT",
        value=(
            f"{verdict_icon} **{verdict}**\n"
            f"RugCheck: "
            f"`{risk_label(risk_level)}`"
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    try:

        score_display = (
            f"{float(score):.0f}"
        )

    except (
        TypeError,
        ValueError,
    ):

        score_display = "—"

    embed.add_field(
        name="RISK SCORE",
        value=(
            f"**{score_display}**\n"
            f"`{clean(risk_level, 'UNKNOWN')}`"
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # AUTHORITIES
    # --------------------------------------------------------

    authorities = (
        "**MINT**\n"
        f"`{authority_status(mint_authority)}`\n"
        f"`{authority_address(mint_authority)}`\n\n"
        "**FREEZE**\n"
        f"`{authority_status(freeze_authority)}`\n"
        f"`{authority_address(freeze_authority)}`"
    )

    embed.add_field(
        name="AUTHORITIES",
        value=authorities,
        inline=True,
    )

    # --------------------------------------------------------
    # HOLDERS
    # --------------------------------------------------------

    embed.add_field(
        name="HOLDER CONCENTRATION",
        value=(
            "TOP HOLDERS\n"
            f"**{format_pct(holders_pct)}**"
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    liquidity_text = (
        f"**${format_number(liquidity)}**"
        if liquidity is not None
        else "—"
    )

    embed.add_field(
        name="LIQUIDITY",
        value=(
            "MARKET LIQUIDITY\n"
            f"{liquidity_text}"
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # TOKEN STATE
    # --------------------------------------------------------

    token_meta = data.get(
        "tokenMeta"
    )

    mutable = None

    if isinstance(
        token_meta,
        dict,
    ):

        mutable = token_meta.get(
            "mutable"
        )

    if mutable is True:

        mutable_text = "YES"

    elif mutable is False:

        mutable_text = "NO"

    else:

        mutable_text = "—"

    embed.add_field(
        name="TOKEN STATE",
        value=(
            f"MUTABLE META  `{mutable_text}`\n"
            f"RISKS         `{len(risks)}`"
        ),
        inline=True,
    )

    # --------------------------------------------------------
    # RISKS
    # --------------------------------------------------------

    if risks:

        risk_lines = []

        for risk in risks[:6]:

            level = (
                risk.get("level")
                or risk.get("severity")
                or risk.get("type")
            )

            risk_name = (
                risk.get("name")
                or risk.get("title")
                or risk.get("description")
                or "Risk detected"
            )

            risk_lines.append(
                f"{risk_emoji(level)} "
                f"**{shorten(risk_name, 55)}**"
            )

        if len(risks) > 6:

            risk_lines.append(
                f"`+{len(risks) - 6} more`"
            )

        risk_text = "\n".join(
            risk_lines
        )

    else:

        risk_text = (
            "🟢 **No listed risks returned.**"
        )

    embed.add_field(
        name="⚠ DETECTED RISKS",
        value=risk_text,
        inline=False,
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    embed.set_footer(
        text=(
            "VEYL • RUGCHECK • "
            "READ-ONLY SECURITY SCREEN"
        )
    )

    return embed


# ============================================================
# VIEW
# ============================================================

class RugCheckView(
    discord.ui.View
):

    def __init__(
        self,
        mint,
        author_id,
    ):

        super().__init__(
            timeout=180
        )

        self.mint = mint

        self.author_id = author_id

    # ========================================================
    # REFRESH
    # ========================================================

    @discord.ui.button(
        label="REFRESH",
        style=discord.ButtonStyle.secondary,
        emoji="↻",
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        if (
            interaction.user.id
            != self.author_id
        ):

            await interaction.response.send_message(
                "This RugCheck panel belongs to another user.",
                ephemeral=True,
            )

            return

        await interaction.response.defer()

        # ----------------------------------------------------
        # Remove cache to force fresh request
        # ----------------------------------------------------

        _cache.pop(
            self.mint,
            None,
        )

        data = await fetch_rugcheck(
            self.mint
        )

        if not data:

            await interaction.followup.send(
                (
                    "⚠️ VEYL could not refresh "
                    "the RugCheck report."
                ),
                ephemeral=True,
            )

            return

        embed = build_rugcheck_embed(
            data,
            self.mint,
        )

        await interaction.message.edit(
            embed=embed,
            view=self,
        )


# ============================================================
# COG
# ============================================================

class RugCheck(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):

        self.bot = bot

        self.cooldowns = {}

        print(
            "⌘ VEYL RugCheck activated."
        )

    # ========================================================
    # /RUGCHECK
    # ========================================================

    @app_commands.command(
        name="rugcheck",
        description=(
            "Scan the risk profile of a Solana token."
        ),
    )
    @app_commands.describe(
        mint=(
            "Solana token mint address"
        )
    )
    async def rugcheck(
        self,
        interaction: discord.Interaction,
        mint: str,
    ):

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        mint = mint.strip()

        if (
            len(mint) < 32
            or len(mint) > 50
        ):

            await interaction.response.send_message(
                (
                    "❌ That doesn't look like a "
                    "valid Solana mint address."
                ),
                ephemeral=True,
            )

            return

        # ----------------------------------------------------
        # COOLDOWN
        # ----------------------------------------------------

        now = time.monotonic()

        last_used = self.cooldowns.get(
            interaction.user.id,
            0,
        )

        if (
            now - last_used
            < COMMAND_COOLDOWN
        ):

            remaining = (
                COMMAND_COOLDOWN
                - (
                    now
                    - last_used
                )
            )

            await interaction.response.send_message(
                (
                    "⏳ VEYL is cooling down. "
                    f"Try again in "
                    f"`{remaining:.1f}s`."
                ),
                ephemeral=True,
            )

            return

        self.cooldowns[
            interaction.user.id
        ] = now

        # ----------------------------------------------------
        # LOADING MESSAGE
        # ----------------------------------------------------

        await interaction.response.send_message(
            (
                "⌘ **VEYL / RUGCHECK**\n\n"
                "Scanning token risk data..."
            ),
            ephemeral=True,
        )

        # ----------------------------------------------------
        # API REQUEST
        # ----------------------------------------------------

        data = await fetch_rugcheck(
            mint
        )

        # ----------------------------------------------------
        # API FAILURE
        # ----------------------------------------------------

        if not data:

            await interaction.edit_original_response(
                content=(
                    "⚠️ **VEYL / RUGCHECK**\n\n"
                    "The RugCheck report could not "
                    "be retrieved right now.\n\n"
                    "Possible causes:\n"
                    "• RugCheck API unavailable\n"
                    "• API rate limit\n"
                    "• Token not found\n"
                    "• Network timeout\n\n"
                    "Check the VEYL terminal for "
                    "the exact API status."
                ),
                embed=None,
                view=None,
            )

            return

        # ----------------------------------------------------
        # BUILD EMBED
        # ----------------------------------------------------

        try:

            embed = build_rugcheck_embed(
                data,
                mint,
            )

        except Exception as error:

            print()
            print(
                "❌ VEYL RugCheck embed error:"
            )
            print(
                f"   {type(error).__name__}: {error}"
            )

            traceback.print_exc()

            await interaction.edit_original_response(
                content=(
                    "⚠️ **VEYL / RUGCHECK**\n\n"
                    "The API responded, but VEYL "
                    "could not build the report."
                ),
                embed=None,
                view=None,
            )

            return

        # ----------------------------------------------------
        # PANEL
        # ----------------------------------------------------

        view = RugCheckView(
            mint,
            interaction.user.id,
        )

        # ----------------------------------------------------
        # FINAL RESPONSE
        # ----------------------------------------------------

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=view,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot,
):

    await bot.add_cog(
        RugCheck(bot)
    )

    print(
        "   ✓ commands.rugcheck"
    )