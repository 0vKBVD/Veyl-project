# ============================================================
# VEYL TOKEN LAB
# SOLANA TOKEN INTELLIGENCE
#
# Command:
#   /tokenlab <mint>
#
# Centralized:
#   Market Hub -> 1544096283038326865
#
# Sources:
#   - DexScreener
#   - RugCheck
#
# Read-only.
# No wallet.
# No private keys.
# No transactions.
# ============================================================

import asyncio
import time
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

MARKET_HUB_ID = 1544096283038326865

DEXSCREENER_URL = (
    "https://api.dexscreener.com/latest/dex/tokens"
)

RUGCHECK_URL = (
    "https://api.rugcheck.xyz/v1"
)

REQUEST_TIMEOUT = 12
GLOBAL_TIMEOUT = 16

CACHE_TTL = 20
COOLDOWN = 5

EMBED_COLOR = 0x18191C


# ============================================================
# CACHE
# ============================================================

_cache = {}
_cooldowns = {}


# ============================================================
# FORMAT HELPERS
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


def shorten(value, length=22):

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


def format_usd(value):

    if value is None:
        return "—"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    if number >= 1:
        return f"${number:,.2f}"

    if number >= 0.01:
        return f"${number:.4f}"

    if number >= 0.000001:
        return f"${number:.8f}"

    return f"${number:.12f}"


def format_percentage(value):

    if value is None:
        return "—"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    if number > 0:
        return f"+{number:.2f}%"

    return f"{number:.2f}%"


def format_integer(value):

    if value is None:
        return "—"

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


# ============================================================
# SOLANA MINT VALIDATION
# ============================================================

def is_probably_solana_mint(mint):

    if not mint:
        return False

    mint = mint.strip()

    if len(mint) < 32 or len(mint) > 50:
        return False

    alphabet = (
        "123456789"
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
    )

    return all(
        character in alphabet
        for character in mint
    )


# ============================================================
# HTTP
# ============================================================

async def get_json(
    url,
    headers=None,
    timeout=REQUEST_TIMEOUT,
):

    timeout_config = aiohttp.ClientTimeout(
        total=timeout,
        connect=5,
        sock_connect=5,
        sock_read=timeout,
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout_config,
            headers=headers or {},
        ) as session:

            async with session.get(
                url,
                allow_redirects=True,
            ) as response:

                status = response.status

                if status == 429:

                    return {
                        "_error": "rate_limit",
                        "_status": status,
                    }

                if status == 404:

                    return {
                        "_error": "not_found",
                        "_status": status,
                    }

                if status >= 500:

                    return {
                        "_error": "server_error",
                        "_status": status,
                    }

                if status != 200:

                    return {
                        "_error": "http_error",
                        "_status": status,
                    }

                try:

                    return await response.json(
                        content_type=None
                    )

                except Exception:

                    return {
                        "_error": "invalid_json",
                        "_status": status,
                    }

    except asyncio.TimeoutError:

        return {
            "_error": "timeout"
        }

    except aiohttp.ClientError as error:

        return {
            "_error": "network",
            "_message": str(error),
        }

    except Exception as error:

        return {
            "_error": "unknown",
            "_message": str(error),
        }


# ============================================================
# DEXSCREENER
# ============================================================

async def fetch_dexscreener(mint):

    url = f"{DEXSCREENER_URL}/{mint}"

    data = await get_json(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "VEYL/5.0",
        },
    )

    if not isinstance(data, dict):
        return None

    if data.get("_error"):

        print(
            "[VEYL TOKEN LAB] "
            f"DexScreener: {data.get('_error')}"
        )

        return None

    pairs = data.get("pairs")

    if not isinstance(pairs, list):
        return None

    solana_pairs = []

    for pair in pairs:

        if not isinstance(pair, dict):
            continue

        if pair.get("chainId") != "solana":
            continue

        solana_pairs.append(pair)

    if not solana_pairs:
        return None

    def liquidity(pair):

        value = (
            pair.get("liquidity", {})
            if isinstance(pair.get("liquidity"), dict)
            else {}
        )

        try:
            return float(value.get("usd") or 0)
        except (TypeError, ValueError):
            return 0

    solana_pairs.sort(
        key=liquidity,
        reverse=True
    )

    return solana_pairs[0]


# ============================================================
# RUGCHECK
# ============================================================

async def fetch_rugcheck(mint):

    url = (
        f"{RUGCHECK_URL}"
        f"/tokens/{mint}/report"
    )

    data = await get_json(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "VEYL/5.0",
        },
    )

    if not isinstance(data, dict):
        return None

    if data.get("_error"):

        print(
            "[VEYL TOKEN LAB] "
            f"RugCheck: {data.get('_error')}"
        )

        return None

    return data


# ============================================================
# CACHE
# ============================================================

def get_cached(mint):

    item = _cache.get(mint)

    if not item:
        return None

    timestamp, data = item

    if time.monotonic() - timestamp > CACHE_TTL:

        _cache.pop(
            mint,
            None
        )

        return None

    return data


def set_cached(mint, data):

    _cache[mint] = (
        time.monotonic(),
        data
    )


# ============================================================
# SCAN ENGINE
# ============================================================

async def scan_token(mint, force=False):

    if not force:

        cached = get_cached(mint)

        if cached:
            return cached

    dex_task = asyncio.create_task(
        fetch_dexscreener(mint)
    )

    rug_task = asyncio.create_task(
        fetch_rugcheck(mint)
    )

    try:

        results = await asyncio.wait_for(
            asyncio.gather(
                dex_task,
                rug_task,
                return_exceptions=True,
            ),
            timeout=GLOBAL_TIMEOUT,
        )

    except asyncio.TimeoutError:

        dex_task.cancel()
        rug_task.cancel()

        return {
            "dex": None,
            "rug": None,
            "timeout": True,
        }

    dex = results[0]
    rug = results[1]

    if isinstance(dex, Exception):
        dex = None

    if isinstance(rug, Exception):
        rug = None

    result = {
        "dex": dex,
        "rug": rug,
        "timeout": False,
        "timestamp": time.time(),
    }

    set_cached(
        mint,
        result
    )

    return result


# ============================================================
# DEX DATA
# ============================================================

def pair_value(pair, key):

    if not pair:
        return None

    return pair.get(key)


def token_name(pair):

    if not pair:
        return "Unknown Token"

    token = pair.get(
        "baseToken",
        {}
    )

    if isinstance(token, dict):

        return token.get(
            "name",
            "Unknown Token"
        )

    return "Unknown Token"


def token_symbol(pair):

    if not pair:
        return "TOKEN"

    token = pair.get(
        "baseToken",
        {}
    )

    if isinstance(token, dict):

        return token.get(
            "symbol",
            "TOKEN"
        )

    return "TOKEN"


def token_price(pair):

    return pair_value(
        pair,
        "priceUsd"
    )


def token_mcap(pair):

    if not pair:
        return None

    return (
        pair.get("marketCap")
        or pair.get("fdv")
    )


def token_liquidity(pair):

    if not pair:
        return None

    liquidity = pair.get(
        "liquidity"
    )

    if not isinstance(
        liquidity,
        dict
    ):
        return None

    return liquidity.get("usd")


def token_volume(pair):

    if not pair:
        return None

    volume = pair.get(
        "volume"
    )

    if not isinstance(
        volume,
        dict
    ):
        return None

    return volume.get("h24")


def token_change(pair):

    if not pair:
        return None

    change = pair.get(
        "priceChange"
    )

    if not isinstance(
        change,
        dict
    ):
        return None

    return change.get("h24")


def pair_dex(pair):

    if not pair:
        return "—"

    return str(
        pair.get(
            "dexId",
            "—"
        )
    ).upper()


def pair_address(pair):

    if not pair:
        return None

    return pair.get(
        "pairAddress"
    )


def pair_url(pair, mint):

    if pair:

        url = pair.get(
            "url"
        )

        if url:
            return url

    return (
        "https://dexscreener.com/"
        f"solana/{mint}"
    )


def pair_transactions(pair):

    if not pair:
        return None, None

    txns = pair.get(
        "txns"
    )

    if not isinstance(
        txns,
        dict
    ):
        return None, None

    h24 = txns.get(
        "h24"
    )

    if not isinstance(
        h24,
        dict
    ):
        return None, None

    return (
        h24.get("buys"),
        h24.get("sells")
    )


# ============================================================
# RUGCHECK DATA
# ============================================================

def rug_value(rug, *keys):

    if not isinstance(
        rug,
        dict
    ):
        return None

    for key in keys:

        value = rug.get(key)

        if value is not None:
            return value

    return None


def rug_risk_level(rug):

    return rug_value(
        rug,
        "riskLevel",
        "risk_level"
    )


def rug_score(rug):

    return rug_value(
        rug,
        "score"
    )


def rug_risks(rug):

    if not rug:
        return []

    risks = rug.get(
        "risks"
    )

    if not isinstance(
        risks,
        list
    ):
        return []

    return [
        risk
        for risk in risks
        if isinstance(
            risk,
            dict
        )
    ]


def rug_authority(rug, key):

    if not rug:
        return None

    value = rug.get(key)

    if value is not None:
        return value

    token = rug.get(
        "token"
    )

    if isinstance(
        token,
        dict
    ):
        return token.get(key)

    return None


def authority_status(value):

    if value is None:
        return "UNKNOWN"

    if isinstance(value, str):

        if not value.strip():
            return "RENOUNCED"

        return "ACTIVE"

    return "ACTIVE"


def top_holder_percentage(rug):

    if not rug:
        return None

    direct = rug_value(
        rug,
        "topHoldersPct",
        "top_holders_pct"
    )

    if direct is not None:
        return direct

    holders = rug.get(
        "topHolders"
    )

    if not isinstance(
        holders,
        list
    ):
        return None

    total = 0.0
    found = False

    for holder in holders:

        if not isinstance(
            holder,
            dict
        ):
            continue

        value = (
            holder.get("pct")
            or holder.get("percentage")
            or holder.get("ownershipPercentage")
        )

        try:

            total += float(value)
            found = True

        except (
            TypeError,
            ValueError
        ):
            pass

    if found:
        return total

    return None


# ============================================================
# RISK ENGINE
# ============================================================

def calculate_verdict(
    rug,
    liquidity,
    holder_pct
):

    if rug:

        level = rug_risk_level(
            rug
        )

        if level:

            level = str(
                level
            ).lower()

            if level in (
                "danger",
                "critical",
                "high"
            ):
                return (
                    "HIGH RISK",
                    "HIGH"
                )

            if level in (
                "warning",
                "medium",
                "moderate"
            ):
                return (
                    "MEDIUM RISK",
                    "MEDIUM"
                )

            if level in (
                "good",
                "safe",
                "low"
            ):
                return (
                    "LOW RISK",
                    "LOW"
                )

    warnings = 0

    try:

        if liquidity is not None:

            value = float(
                liquidity
            )

            if value < 5_000:
                warnings += 2

            elif value < 20_000:
                warnings += 1

    except (
        TypeError,
        ValueError
    ):
        pass

    try:

        if holder_pct is not None:

            value = float(
                holder_pct
            )

            if value > 50:
                warnings += 2

            elif value > 30:
                warnings += 1

    except (
        TypeError,
        ValueError
    ):
        pass

    if warnings >= 3:

        return (
            "HIGH RISK",
            "HIGH"
        )

    if warnings >= 1:

        return (
            "CAUTION",
            "MEDIUM"
        )

    if rug or liquidity is not None:

        return (
            "LOWER RISK",
            "LOW"
        )

    return (
        "INSUFFICIENT DATA",
        "UNKNOWN"
    )


def risk_icon(level):

    if level == "HIGH":
        return "!"
    if level == "MEDIUM":
        return "~"
    if level == "LOW":
        return "+"
    return "?"


# ============================================================
# EMBED
# ============================================================

def build_embed(
    mint,
    result
):

    pair = result.get(
        "dex"
    )

    rug = result.get(
        "rug"
    )

    timeout = result.get(
        "timeout",
        False
    )

    name = token_name(pair)
    symbol = token_symbol(pair)

    liquidity = token_liquidity(
        pair
    )

    holder_pct = top_holder_percentage(
        rug
    )

    verdict, verdict_level = calculate_verdict(
        rug,
        liquidity,
        holder_pct
    )

    embed = discord.Embed(
        title="VEYL / TOKEN LAB",
        description=(
            f"**{name}** · `{symbol}`\n"
            f"`{shorten(mint, 44)}`"
        ),
        color=EMBED_COLOR
    )

    # --------------------------------------------------------
    # VERDICT
    # --------------------------------------------------------

    embed.add_field(
        name="VEYL VERDICT",
        value=(
            f"`{risk_icon(verdict_level)}` "
            f"**{verdict}**\n"
            "Automated token screening"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    embed.add_field(
        name="PRICE",
        value=(
            f"**{format_usd(token_price(pair))}**\n"
            f"24H `{format_percentage(token_change(pair))}`"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # MARKET
    # --------------------------------------------------------

    embed.add_field(
        name="MARKET",
        value=(
            f"MCAP  **${format_number(token_mcap(pair))}**\n"
            f"LIQ   **${format_number(liquidity)}**"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # FLOW
    # --------------------------------------------------------

    buys, sells = pair_transactions(
        pair
    )

    embed.add_field(
        name="24H FLOW",
        value=(
            f"VOLUME **${format_number(token_volume(pair))}**\n"
            f"BUYS `{format_integer(buys)}`\n"
            f"SELLS `{format_integer(sells)}`"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # VENUE
    # --------------------------------------------------------

    embed.add_field(
        name="MARKET VENUE",
        value=(
            f"DEX **{pair_dex(pair)}**\n"
            f"PAIR `{shorten(pair_address(pair), 28)}`"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # RUGCHECK
    # --------------------------------------------------------

    if rug:

        level = rug_risk_level(
            rug
        )

        score = rug_score(
            rug
        )

        embed.add_field(
            name="RUGCHECK",
            value=(
                f"LEVEL **{clean(level, 'UNKNOWN')}**\n"
                f"SCORE **{clean(score)}**"
            ),
            inline=True
        )

    else:

        embed.add_field(
            name="RUGCHECK",
            value=(
                "`?` **UNAVAILABLE**\n"
                "External risk data unavailable"
            ),
            inline=True
        )

    # --------------------------------------------------------
    # AUTHORITIES
    # --------------------------------------------------------

    if rug:

        mint_authority = rug_authority(
            rug,
            "mintAuthority"
        )

        freeze_authority = rug_authority(
            rug,
            "freezeAuthority"
        )

        embed.add_field(
            name="AUTHORITIES",
            value=(
                f"MINT   `{authority_status(mint_authority)}`\n"
                f"FREEZE `{authority_status(freeze_authority)}`"
            ),
            inline=True
        )

    # --------------------------------------------------------
    # HOLDERS
    # --------------------------------------------------------

    embed.add_field(
        name="HOLDER CONCENTRATION",
        value=(
            f"TOP HOLDERS\n"
            f"**{format_percentage(holder_pct)}**"
        ),
        inline=True
    )

    # --------------------------------------------------------
    # RISKS
    # --------------------------------------------------------

    risks = rug_risks(
        rug
    )

    if risks:

        lines = []

        for risk in risks[:6]:

            level = (
                risk.get("level")
                or risk.get("severity")
                or risk.get("type")
                or "unknown"
            )

            title = (
                risk.get("name")
                or risk.get("title")
                or risk.get("description")
                or "Risk detected"
            )

            lines.append(
                f"`{risk_icon(str(level).upper())}` "
                f"**{shorten(title, 62)}**"
            )

        if len(risks) > 6:

            lines.append(
                f"`+{len(risks) - 6} more`"
            )

        risk_text = "\n".join(
            lines
        )

    elif rug:

        risk_text = (
            "`+` **No listed risks returned.**"
        )

    else:

        risk_text = (
            "`?` **Risk data unavailable.**"
        )

    embed.add_field(
        name="DETECTED RISKS",
        value=risk_text,
        inline=False
    )

    # --------------------------------------------------------
    # NOTICE
    # --------------------------------------------------------

    if timeout:

        embed.add_field(
            name="SYSTEM NOTICE",
            value=(
                "Some external sources did not respond "
                "within the scan window."
            ),
            inline=False
        )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    embed.set_footer(
        text=(
            "VEYL • TOKEN LAB • "
            "READ-ONLY INTELLIGENCE"
        )
    )

    return embed


# ============================================================
# VIEW
# ============================================================

class TokenLabView(
    discord.ui.View
):

    def __init__(
        self,
        mint,
        author_id
    ):

        super().__init__(
            timeout=300
        )

        self.mint = mint
        self.author_id = author_id

        # ----------------------------------------------------
        # Link button
        # IMPORTANT:
        # discord.ui.Button is used directly.
        # ----------------------------------------------------

        self.add_item(
            discord.ui.Button(
                label="DEXSCREENER",
                style=discord.ButtonStyle.link,
                url=(
                    "https://dexscreener.com/"
                    f"solana/{mint}"
                )
            )
        )

    # ========================================================
    # REFRESH
    # ========================================================

    @discord.ui.button(
        label="REFRESH",
        style=discord.ButtonStyle.secondary
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.author_id:

            await interaction.response.send_message(
                "This Token Lab panel belongs to another user.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        try:

            result = await asyncio.wait_for(
                scan_token(
                    self.mint,
                    force=True
                ),
                timeout=GLOBAL_TIMEOUT + 3
            )

            embed = build_embed(
                self.mint,
                result
            )

            await interaction.message.edit(
                embed=embed,
                view=self
            )

        except asyncio.TimeoutError:

            await interaction.followup.send(
                "Token Lab refresh timed out.",
                ephemeral=True
            )

        except discord.HTTPException as error:

            print()
            print(
                "=========================================="
            )
            print(
                " VEYL TOKEN LAB / DISCORD ERROR"
            )
            print(
                "=========================================="
            )
            print(
                f"HTTP STATUS : {error.status}"
            )
            print(
                f"ERROR       : {error}"
            )
            print(
                "=========================================="
            )

            await interaction.followup.send(
                "Discord rejected the Token Lab update.",
                ephemeral=True
            )

        except Exception as error:

            print(
                "[VEYL TOKEN LAB] Refresh error:",
                type(error).__name__,
                error
            )

            await interaction.followup.send(
                "Token Lab encountered an internal error.",
                ephemeral=True
            )


# ============================================================
# COG
# ============================================================

class TokenLab(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "VEYL Token Lab activated."
        )

    # ========================================================
    # /TOKENLAB
    # ========================================================

    @app_commands.command(
        name="tokenlab",
        description=(
            "Open VEYL Token Lab for a Solana token."
        )
    )
    @app_commands.describe(
        mint=(
            "Solana token mint address"
        )
    )
    async def tokenlab(
        self,
        interaction: discord.Interaction,
        mint: str
    ):

        mint = mint.strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not is_probably_solana_mint(
            mint
        ):

            await interaction.response.send_message(
                (
                    "**Invalid Solana mint address.**\n\n"
                    "Paste the token mint address, "
                    "not the pair name."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # MARKET HUB
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(
                "Token Lab is only available inside the VEYL server.",
                ephemeral=True
            )

            return

        market_hub = interaction.guild.get_channel(
            MARKET_HUB_ID
        )

        if market_hub is None:

            await interaction.response.send_message(
                (
                    "VEYL could not find the configured "
                    "Market Hub channel."
                ),
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # COOLDOWN
        # ----------------------------------------------------

        now = time.monotonic()

        last = _cooldowns.get(
            interaction.user.id,
            0
        )

        elapsed = now - last

        if elapsed < COOLDOWN:

            remaining = COOLDOWN - elapsed

            await interaction.response.send_message(
                (
                    f"VEYL is cooling down. "
                    f"Try again in `{remaining:.1f}s`."
                ),
                ephemeral=True
            )

            return

        _cooldowns[
            interaction.user.id
        ] = now

        # ----------------------------------------------------
        # INITIAL RESPONSE
        # ----------------------------------------------------

        await interaction.response.send_message(
            (
                "VEYL Token Lab is scanning the token..."
            ),
            ephemeral=True
        )

        # ----------------------------------------------------
        # SCAN
        # ----------------------------------------------------

        try:

            result = await asyncio.wait_for(
                scan_token(
                    mint
                ),
                timeout=GLOBAL_TIMEOUT + 3
            )

        except asyncio.TimeoutError:

            await interaction.edit_original_response(
                content=(
                    "Token Lab timed out while "
                    "contacting external data sources."
                )
            )

            return

        except Exception as error:

            print(
                "[VEYL TOKEN LAB] Scan error:",
                type(error).__name__,
                error
            )

            await interaction.edit_original_response(
                content=(
                    "Token Lab encountered an internal error."
                )
            )

            return

        # ----------------------------------------------------
        # NO DATA
        # ----------------------------------------------------

        if (
            not result.get("dex")
            and not result.get("rug")
        ):

            await interaction.edit_original_response(
                content=(
                    "**Token Lab could not find this token.**\n\n"
                    "Make sure you pasted the **token mint "
                    "address**, not the pair address."
                )
            )

            return

        # ----------------------------------------------------
        # BUILD
        # ----------------------------------------------------

        embed = build_embed(
            mint,
            result
        )

        view = TokenLabView(
            mint,
            interaction.user.id
        )

        # ----------------------------------------------------
        # CENTRAL MARKET HUB
        # ----------------------------------------------------

        try:

            await market_hub.send(
                embed=embed,
                view=view
            )

        except discord.Forbidden:

            await interaction.edit_original_response(
                content=(
                    "Token Lab found the Market Hub, "
                    "but VEYL does not have permission "
                    "to send messages there."
                )
            )

            return

        except discord.HTTPException as error:

            print()
            print(
                "=========================================="
            )
            print(
                " VEYL TOKEN LAB / DISCORD ERROR"
            )
            print(
                "=========================================="
            )
            print(
                f"HTTP STATUS : {error.status}"
            )
            print(
                f"ERROR       : {error}"
            )
            print(
                "TEXT        : {0}".format(error)
            )
            print(
                "CODE        : 50035"
                if error.status == 400
                else "CODE        : UNKNOWN"
            )
            print(
                "=========================================="
            )

            await interaction.edit_original_response(
                content=(
                    "Token Lab completed the scan, "
                    "but Discord rejected the result."
                )
            )

            return

        # ----------------------------------------------------
        # DONE
        # ----------------------------------------------------

        await interaction.edit_original_response(
            content=(
                f"Token Lab scan complete. "
                f"Result posted in <#{MARKET_HUB_ID}>."
            )
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        TokenLab(bot)
    )

    print(
        "   VEYL Token Lab loaded."
    )