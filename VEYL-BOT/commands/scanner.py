# ============================================================
# VEYL SCANNER
# SOLANA TOKEN INTELLIGENCE
#
# Command:
#   /scanner <mint>
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
from typing import Optional, Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens"
RUGCHECK_URL = "https://api.rugcheck.xyz/v1"

REQUEST_TIMEOUT = 12
GLOBAL_TIMEOUT = 15

CACHE_TTL = 20
COMMAND_COOLDOWN = 5

EMBED_COLOR = 0x18191C

_cache = {}
_cooldowns = {}


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


def shorten(value, length=20):
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


def format_price(value):
    if value is None:
        return "—"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    if number == 0:
        return "$0"

    if number >= 1:
        return f"${number:,.4f}"

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

    sign = "+" if number > 0 else ""

    return f"{sign}{number:.2f}%"


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
        "safe",
        "low",
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

    return mapping.get(level, level)


def is_probably_solana_mint(mint):
    if not mint:
        return False

    mint = mint.strip()

    if len(mint) < 32 or len(mint) > 50:
        return False

    allowed = (
        "123456789"
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
    )

    return all(char in allowed for char in mint)


# ============================================================
# HTTP
# ============================================================

async def http_get_json(
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
                    print(
                        f"[VEYL SCANNER] HTTP 429: {url}"
                    )

                    return {
                        "_error": "rate_limit",
                        "_status": status,
                    }

                if status == 404:
                    print(
                        f"[VEYL SCANNER] HTTP 404: {url}"
                    )

                    return {
                        "_error": "not_found",
                        "_status": status,
                    }

                if status >= 500:
                    print(
                        f"[VEYL SCANNER] HTTP {status}: {url}"
                    )

                    return {
                        "_error": "server_error",
                        "_status": status,
                    }

                if status != 200:
                    print(
                        f"[VEYL SCANNER] HTTP {status}: {url}"
                    )

                    return {
                        "_error": "http_error",
                        "_status": status,
                    }

                try:
                    data = await response.json(
                        content_type=None
                    )
                except Exception as error:
                    print(
                        "[VEYL SCANNER] Invalid JSON:",
                        error,
                    )

                    return {
                        "_error": "invalid_json",
                        "_status": status,
                    }

                return data

    except asyncio.TimeoutError:
        print(
            f"[VEYL SCANNER] Timeout: {url}"
        )

        return {
            "_error": "timeout"
        }

    except aiohttp.ClientError as error:
        print(
            "[VEYL SCANNER] Network error:",
            error,
        )

        return {
            "_error": "network",
            "_message": str(error),
        }

    except Exception as error:
        print(
            "[VEYL SCANNER] HTTP error:",
            type(error).__name__,
            error,
        )

        return {
            "_error": "unknown",
            "_message": str(error),
        }


# ============================================================
# DEXSCREENER
# ============================================================

async def fetch_dexscreener(mint):
    url = f"{DEXSCREENER_URL}/{mint}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "VEYL/5.0",
    }

    data = await http_get_json(
        url,
        headers=headers,
    )

    if not isinstance(data, dict):
        return None

    if data.get("_error"):
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

    def liquidity_value(pair):
        liquidity = pair.get("liquidity")

        if not isinstance(liquidity, dict):
            return 0

        try:
            return float(
                liquidity.get("usd") or 0
            )
        except (TypeError, ValueError):
            return 0

    solana_pairs.sort(
        key=liquidity_value,
        reverse=True,
    )

    return solana_pairs[0]


# ============================================================
# RUGCHECK
# ============================================================

async def fetch_rugcheck(mint):
    url = f"{RUGCHECK_URL}/tokens/{mint}/report"

    headers = {
        "Accept": "application/json",
        "User-Agent": "VEYL/5.0",
    }

    data = await http_get_json(
        url,
        headers=headers,
    )

    if not isinstance(data, dict):
        return None

    if data.get("_error"):
        return None

    return data


# ============================================================
# CACHE
# ============================================================

def get_cache(mint):
    cached = _cache.get(mint)

    if not cached:
        return None

    timestamp, data = cached

    if time.monotonic() - timestamp > CACHE_TTL:
        _cache.pop(mint, None)
        return None

    return data


def set_cache(mint, data):
    _cache[mint] = (
        time.monotonic(),
        data,
    )


# ============================================================
# SCANNER ENGINE
# ============================================================

async def scan_token(mint):
    cached = get_cache(mint)

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
        print(
            "[VEYL SCANNER] Global scan timeout."
        )

        for task in (
            dex_task,
            rug_task,
        ):
            if not task.done():
                task.cancel()

        return {
            "dex": None,
            "rug": None,
            "timeout": True,
        }

    except Exception as error:
        print(
            "[VEYL SCANNER] Engine error:",
            type(error).__name__,
            error,
        )

        return {
            "dex": None,
            "rug": None,
            "timeout": False,
        }

    dex_data = results[0]
    rug_data = results[1]

    if isinstance(
        dex_data,
        Exception,
    ):
        print(
            "[VEYL SCANNER] Dex exception:",
            dex_data,
        )
        dex_data = None

    if isinstance(
        rug_data,
        Exception,
    ):
        print(
            "[VEYL SCANNER] RugCheck exception:",
            rug_data,
        )
        rug_data = None

    result = {
        "dex": dex_data,
        "rug": rug_data,
        "timeout": False,
    }

    set_cache(
        mint,
        result,
    )

    return result


# ============================================================
# DEX DATA
# ============================================================

def get_pair_token_name(pair):
    if not pair:
        return "Unknown Token"

    base = pair.get(
        "baseToken",
        {},
    )

    if isinstance(base, dict):
        name = base.get("name")

        if name:
            return str(name)

    return "Unknown Token"


def get_pair_symbol(pair):
    if not pair:
        return "TOKEN"

    base = pair.get(
        "baseToken",
        {},
    )

    if isinstance(base, dict):
        symbol = base.get("symbol")

        if symbol:
            return str(symbol)

    return "TOKEN"


def get_dex_name(pair):
    if not pair:
        return "—"

    return str(
        pair.get(
            "dexId",
            "—",
        )
    ).upper()


def get_liquidity(pair):
    if not pair:
        return None

    liquidity = pair.get(
        "liquidity"
    )

    if not isinstance(
        liquidity,
        dict,
    ):
        return None

    return liquidity.get("usd")


def get_market_cap(pair):
    if not pair:
        return None

    return (
        pair.get("marketCap")
        or pair.get("fdv")
    )


def get_volume(pair):
    if not pair:
        return None

    volume = pair.get(
        "volume"
    )

    if not isinstance(
        volume,
        dict,
    ):
        return None

    return volume.get("h24")


def get_price(pair):
    if not pair:
        return None

    return pair.get("priceUsd")


def get_price_change(pair):
    if not pair:
        return None

    changes = pair.get(
        "priceChange"
    )

    if not isinstance(
        changes,
        dict,
    ):
        return None

    return changes.get("h24")


def get_tx_count(pair):
    if not pair:
        return None

    txns = pair.get(
        "txns"
    )

    if not isinstance(
        txns,
        dict,
    ):
        return None

    h24 = txns.get(
        "h24"
    )

    if not isinstance(
        h24,
        dict,
    ):
        return None

    buys = h24.get(
        "buys",
        0,
    )

    sells = h24.get(
        "sells",
        0,
    )

    try:
        return int(buys) + int(sells)
    except (TypeError, ValueError):
        return None


def get_buy_sell(pair):
    if not pair:
        return None, None

    txns = pair.get(
        "txns"
    )

    if not isinstance(
        txns,
        dict,
    ):
        return None, None

    h24 = txns.get(
        "h24"
    )

    if not isinstance(
        h24,
        dict,
    ):
        return None, None

    return (
        h24.get("buys"),
        h24.get("sells"),
    )


# ============================================================
# RUGCHECK DATA
# ============================================================

def rug_value(data, *keys):
    if not isinstance(
        data,
        dict,
    ):
        return None

    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return None


def extract_risk_level(rug):
    if not rug:
        return None

    return rug_value(
        rug,
        "riskLevel",
        "risk_level",
    )


def extract_risk_score(rug):
    if not rug:
        return None

    return rug_value(
        rug,
        "score",
    )


def extract_risks(rug):
    if not rug:
        return []

    risks = rug.get(
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


def extract_authority(rug, key):
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
        dict,
    ):
        return token.get(key)

    return None


def authority_text(value):
    if value is None:
        return "RENOUNCED"

    if isinstance(
        value,
        str,
    ):
        if not value.strip():
            return "RENOUNCED"

        return "ACTIVE"

    return "ACTIVE"


def extract_top_holder_pct(rug):
    if not rug:
        return None

    direct = rug_value(
        rug,
        "topHoldersPct",
        "top_holders_pct",
    )

    if direct is not None:
        return direct

    holders = rug.get(
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
            ValueError,
        ):
            continue

    return total if found else None


# ============================================================
# VERDICT
# ============================================================

def calculate_verdict(
    rug,
    liquidity,
    holders_pct,
):
    if rug:
        level = extract_risk_level(rug)

        if level:
            level = str(
                level
            ).lower()

            if level in (
                "danger",
                "critical",
                "high",
            ):
                return (
                    "🔴",
                    "HIGH RISK",
                )

            if level in (
                "warning",
                "medium",
                "moderate",
            ):
                return (
                    "🟠",
                    "MEDIUM RISK",
                )

            if level in (
                "good",
                "safe",
                "low",
            ):
                return (
                    "🟢",
                    "LOW RISK",
                )

    warnings = 0

    try:
        if liquidity is not None:
            liquidity_value = float(
                liquidity
            )

            if liquidity_value < 5_000:
                warnings += 2

            elif liquidity_value < 20_000:
                warnings += 1

    except (
        TypeError,
        ValueError,
    ):
        pass

    try:
        if holders_pct is not None:
            holder_value = float(
                holders_pct
            )

            if holder_value > 50:
                warnings += 2

            elif holder_value > 30:
                warnings += 1

    except (
        TypeError,
        ValueError,
    ):
        pass

    if warnings >= 3:
        return (
            "🔴",
            "HIGH RISK",
        )

    if warnings >= 1:
        return (
            "🟠",
            "CAUTION",
        )

    if rug or liquidity is not None:
        return (
            "🟢",
            "LOWER RISK",
        )

    return (
        "⚪",
        "INSUFFICIENT DATA",
    )


# ============================================================
# EMBED
# ============================================================

def build_scanner_embed(
    mint,
    result,
):
    pair = result.get("dex")
    rug = result.get("rug")
    timeout = result.get(
        "timeout",
        False,
    )

    name = get_pair_token_name(
        pair
    )

    symbol = get_pair_symbol(
        pair
    )

    liquidity = get_liquidity(
        pair
    )

    holders_pct = extract_top_holder_pct(
        rug
    )

    emoji, verdict = calculate_verdict(
        rug,
        liquidity,
        holders_pct,
    )

    embed = discord.Embed(
        title="⌘ VEYL / SCANNER",
        description=(
            f"**{name}** · `{symbol}`\n"
            f"`{shorten(mint, 40)}`"
        ),
        color=EMBED_COLOR,
    )

    # ========================================================
    # VERDICT
    # ========================================================

    embed.add_field(
        name="◈ VEYL VERDICT",
        value=(
            f"{emoji} **{verdict}**\n"
            "Automated token screening"
        ),
        inline=True,
    )

    # ========================================================
    # PRICE
    # ========================================================

    embed.add_field(
        name="PRICE",
        value=(
            f"**{format_price(get_price(pair))}**\n"
            f"24H {format_percentage(get_price_change(pair))}"
        ),
        inline=True,
    )

    # ========================================================
    # MARKET
    # ========================================================

    embed.add_field(
        name="MARKET",
        value=(
            f"MCAP  **${format_number(get_market_cap(pair))}**\n"
            f"LIQ   **${format_number(liquidity)}**"
        ),
        inline=True,
    )

    # ========================================================
    # VOLUME
    # ========================================================

    buys, sells = get_buy_sell(
        pair
    )

    embed.add_field(
        name="24H FLOW",
        value=(
            f"VOLUME  **${format_number(get_volume(pair))}**\n"
            f"TXNS    **{format_number(get_tx_count(pair))}**\n"
            f"BUYS    `{clean(buys)}` · SELLS `{clean(sells)}`"
        ),
        inline=True,
    )

    # ========================================================
    # DEX
    # ========================================================

    pair_address = None

    if pair:
        pair_address = pair.get(
            "pairAddress"
        )

    embed.add_field(
        name="LIQUIDITY VENUE",
        value=(
            f"DEX  **{get_dex_name(pair)}**\n"
            f"PAIR `{shorten(pair_address, 24)}`"
        ),
        inline=True,
    )

    # ========================================================
    # RUGCHECK
    # ========================================================

    risk_level = extract_risk_level(
        rug
    )

    risk_score = extract_risk_score(
        rug
    )

    if rug:
        embed.add_field(
            name="RUGCHECK",
            value=(
                f"LEVEL  **{risk_label(risk_level)}**\n"
                f"SCORE  **{clean(risk_score)}**"
            ),
            inline=True,
        )

    else:
        embed.add_field(
            name="RUGCHECK",
            value=(
                "⚪ **UNAVAILABLE**\n"
                "RugCheck data unavailable."
            ),
            inline=True,
        )

    # ========================================================
    # AUTHORITIES
    # ========================================================

    if rug:
        mint_authority = extract_authority(
            rug,
            "mintAuthority",
        )

        freeze_authority = extract_authority(
            rug,
            "freezeAuthority",
        )

        authorities = (
            f"MINT   `{authority_text(mint_authority)}`\n"
            f"FREEZE `{authority_text(freeze_authority)}`"
        )

        embed.add_field(
            name="AUTHORITIES",
            value=authorities,
            inline=True,
        )

    # ========================================================
    # HOLDERS
    # ========================================================

    holder_text = (
        format_percentage(holders_pct)
        if holders_pct is not None
        else "—"
    )

    embed.add_field(
        name="HOLDER CONCENTRATION",
        value=(
            "TOP HOLDERS\n"
            f"**{holder_text}**"
        ),
        inline=True,
    )

    # ========================================================
    # RISKS
    # ========================================================

    risks = extract_risks(
        rug
    )

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
                or "Risk detected"
            )

            risk_lines.append(
                f"{risk_emoji(level)} "
                f"**{shorten(risk_name, 60)}**"
            )

        if len(risks) > 6:
            risk_lines.append(
                f"`+{len(risks) - 6} more`"
            )

        risk_text = "\n".join(
            risk_lines
        )

    elif rug:
        risk_text = (
            "🟢 **No listed risks returned.**"
        )

    else:
        risk_text = (
            "⚪ **Risk data unavailable.**"
        )

    embed.add_field(
        name="⚠ DETECTED RISKS",
        value=risk_text,
        inline=False,
    )

    # ========================================================
    # TIMEOUT NOTICE
    # ========================================================

    if timeout:
        embed.add_field(
            name="SYSTEM NOTICE",
            value=(
                "⚠️ The scan reached its time limit. "
                "Some external data may be unavailable."
            ),
            inline=False,
        )

    # ========================================================
    # FOOTER
    # ========================================================

    embed.set_footer(
        text=(
            "VEYL • SCANNER • READ-ONLY "
            "TOKEN INTELLIGENCE"
        )
    )

    return embed


# ============================================================
# VIEW
# ============================================================

class ScannerView(
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

        # ====================================================
        # LINK BUTTON
        #
        # IMPORTANT:
        # We create this manually.
        # No emoji is used because Discord was rejecting it.
        # ====================================================

        self.add_item(
            discord.ui.Button(
                label="DEXSCREENER",
                style=discord.ButtonStyle.link,
                url=(
                    f"https://dexscreener.com/solana/{mint}"
                ),
            )
        )

    # ========================================================
    # REFRESH BUTTON
    # ========================================================

    @discord.ui.button(
        label="REFRESH",
        style=discord.ButtonStyle.secondary,
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This scanner panel belongs to another user.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Force fresh data
        _cache.pop(
            self.mint,
            None,
        )

        try:
            result = await asyncio.wait_for(
                scan_token(
                    self.mint
                ),
                timeout=GLOBAL_TIMEOUT + 2,
            )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                (
                    "⚠️ **VEYL / SCANNER**\n\n"
                    "The refresh timed out."
                ),
                ephemeral=True,
            )
            return

        except Exception as error:
            print(
                "[VEYL SCANNER] Refresh error:",
                type(error).__name__,
                error,
            )

            await interaction.followup.send(
                (
                    "⚠️ **VEYL / SCANNER**\n\n"
                    "An internal scanner error occurred."
                ),
                ephemeral=True,
            )
            return

        embed = build_scanner_embed(
            self.mint,
            result,
        )

        try:
            await interaction.message.edit(
                embed=embed,
                view=self,
            )

        except discord.NotFound:
            await interaction.followup.send(
                "The scanner message no longer exists.",
                ephemeral=True,
            )

        except discord.HTTPException as error:
            print(
                "[VEYL SCANNER] Discord edit error:",
                error,
            )

            await interaction.followup.send(
                "VEYL couldn't update the scanner panel.",
                ephemeral=True,
            )


# ============================================================
# COG
# ============================================================

class Scanner(
    commands.Cog
):

    def __init__(
        self,
        bot,
    ):
        self.bot = bot

        print(
            "⌘ VEYL Scanner activated."
        )

    # ========================================================
    # /SCANNER
    # ========================================================

    @app_commands.command(
        name="scanner",
        description=(
            "Scan a Solana token for market and risk data."
        ),
    )
    @app_commands.describe(
        mint=(
            "Solana token mint address"
        )
    )
    async def scanner(
        self,
        interaction: discord.Interaction,
        mint: str,
    ):
        # ====================================================
        # CLEAN
        # ====================================================

        mint = mint.strip()

        # ====================================================
        # VALIDATION
        # ====================================================

        if not is_probably_solana_mint(
            mint
        ):
            await interaction.response.send_message(
                (
                    "❌ **Invalid Solana mint address.**\n\n"
                    "Paste the token's mint address, "
                    "not the pair address."
                ),
                ephemeral=True,
            )
            return

        # ====================================================
        # COOLDOWN
        # ====================================================

        now = time.monotonic()

        last = _cooldowns.get(
            interaction.user.id,
            0,
        )

        elapsed = now - last

        if elapsed < COMMAND_COOLDOWN:
            remaining = (
                COMMAND_COOLDOWN
                - elapsed
            )

            await interaction.response.send_message(
                (
                    f"⏳ VEYL is cooling down. "
                    f"Try again in `{remaining:.1f}s`."
                ),
                ephemeral=True,
            )
            return

        _cooldowns[
            interaction.user.id
        ] = now

        # ====================================================
        # LOADING
        # ====================================================

        await interaction.response.send_message(
            (
                "⌘ **VEYL / SCANNER**\n\n"
                "Scanning token intelligence..."
            ),
            ephemeral=True,
        )

        # ====================================================
        # SCAN
        # ====================================================

        try:
            result = await asyncio.wait_for(
                scan_token(
                    mint
                ),
                timeout=GLOBAL_TIMEOUT + 2,
            )

        except asyncio.TimeoutError:
            await interaction.edit_original_response(
                content=(
                    "⚠️ **VEYL / SCANNER**\n\n"
                    "The scan timed out.\n"
                    "The external market APIs did not respond "
                    "in time."
                ),
                embed=None,
                view=None,
            )
            return

        except Exception as error:
            print(
                "[VEYL SCANNER] Command error:",
                type(error).__name__,
                error,
            )

            await interaction.edit_original_response(
                content=(
                    "⚠️ **VEYL / SCANNER**\n\n"
                    "An internal scanner error occurred.\n"
                    "Check the VEYL terminal."
                ),
                embed=None,
                view=None,
            )
            return

        # ====================================================
        # NO DATA
        # ====================================================

        if (
            not result.get("dex")
            and not result.get("rug")
        ):
            await interaction.edit_original_response(
                content=(
                    "⚠️ **VEYL / SCANNER**\n\n"
                    "No market or risk data could be retrieved "
                    "for this mint.\n\n"
                    "Make sure you pasted the **token mint "
                    "address**, not the pair address."
                ),
                embed=None,
                view=None,
            )
            return

        # ====================================================
        # BUILD EMBED
        # ====================================================

        embed = build_scanner_embed(
            mint,
            result,
        )

        view = ScannerView(
            mint,
            interaction.user.id,
        )

        # ====================================================
        # DISCORD RESPONSE
        # ====================================================

        try:
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=view,
            )

            print(
                "[VEYL SCANNER] Scan displayed successfully."
            )

        except discord.HTTPException as error:
            print(
                "\n"
                "==========================================\n"
                " VEYL SCANNER / DISCORD ERROR\n"
                "==========================================\n"
                f"HTTP STATUS : {error.status}\n"
                f"ERROR       : {error}\n"
                f"TEXT        : {getattr(error, 'text', '—')}\n"
                f"CODE        : {getattr(error, 'code', '—')}\n"
                "==========================================\n"
            )

            # Fallback WITHOUT components.
            # This prevents Discord from rejecting the
            # complete response if a component is invalid.

            try:
                await interaction.edit_original_response(
                    content=(
                        "⌘ **VEYL / SCANNER**\n\n"
                        "The scan completed successfully.\n\n"
                        f"**Token:** `{shorten(mint, 32)}`\n\n"
                        "Discord rejected one of the display "
                        "components, so VEYL returned the raw "
                        "scan without buttons."
                    ),
                    embed=embed,
                    view=None,
                )

            except Exception as fallback_error:
                print(
                    "[VEYL SCANNER] Fallback error:",
                    type(fallback_error).__name__,
                    fallback_error,
                )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(
        Scanner(bot)
    )

    print(
        "   ✓ commands.scanner"
    )