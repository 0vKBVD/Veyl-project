"""Discord application command for the VEYL market radar."""

import asyncio
from collections.abc import Iterable

import discord
from discord import app_commands
from discord.ext import commands

from services.assets import PREDICT_ASSETS
from services.market import get_market_data


RADAR_TIMEOUT = 30
MOVERS_LIMIT = 5


def as_float(value):
    """Return a numeric market value, or ``None`` when it is unavailable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_price(value):
    if value is None:
        return "—"
    if value >= 1_000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:,.4f}"
    if value >= 0.01:
        return f"${value:,.5f}"
    return f"${value:,.8f}"


def format_volume(value):
    if value is None:
        return "—"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.0f}"


def format_movers(snapshots: Iterable[dict]):
    lines = []
    for position, snapshot in enumerate(snapshots, start=1):
        lines.append(
            f"`{position}` **{snapshot['symbol']}** "
            f"`{format_price(snapshot['price'])}` "
            f"`{snapshot['change']:+.2f}%`"
        )
    return "\n".join(lines) or "No qualifying market data."


def market_read(average_change, positive, negative):
    if average_change >= 2 and positive > negative:
        return "Broad positive momentum across the VEYL asset universe."
    if average_change <= -2 and negative > positive:
        return "Broad selling pressure across the VEYL asset universe."
    if positive > negative:
        return "Positive breadth, with gains spread across the tracked assets."
    if negative > positive:
        return "Negative breadth, with losses spread across the tracked assets."
    return "Mixed market conditions; no directional breadth advantage."


def build_radar_embed(snapshots):
    gainers = sorted(
        snapshots,
        key=lambda snapshot: snapshot["change"],
        reverse=True,
    )[:MOVERS_LIMIT]
    losers = sorted(
        snapshots,
        key=lambda snapshot: snapshot["change"],
    )[:MOVERS_LIMIT]

    positive = sum(snapshot["change"] > 0 for snapshot in snapshots)
    negative = sum(snapshot["change"] < 0 for snapshot in snapshots)
    unchanged = len(snapshots) - positive - negative
    average_change = sum(snapshot["change"] for snapshot in snapshots) / len(snapshots)
    total_volume = sum(
        snapshot["volume"]
        for snapshot in snapshots
        if snapshot["volume"] is not None
    )
    providers = sorted(
        {
            snapshot["provider"]
            for snapshot in snapshots
            if snapshot["provider"]
        }
    )

    if average_change > 0:
        color = discord.Color.green()
    elif average_change < 0:
        color = discord.Color.red()
    else:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title="⌘ VEYL // MARKET RADAR",
        description=(
            "```text\n"
            "MARKET RADAR // 24H WINDOW\n"
            "────────────────────────────────\n"
            f"UNIVERSE    {len(PREDICT_ASSETS)} VEYL ASSETS\n"
            f"COVERAGE    {len(snapshots)}/{len(PREDICT_ASSETS)} RESPONSES\n"
            "────────────────────────────────\n"
            "```\n"
            f"**{market_read(average_change, positive, negative)}**"
        ),
        color=color,
    )

    embed.add_field(
        name="▲ TOP MOMENTUM",
        value=format_movers(gainers),
        inline=True,
    )
    embed.add_field(
        name="▼ MARKET PRESSURE",
        value=format_movers(losers),
        inline=True,
    )
    embed.add_field(
        name="◈ MARKET BREADTH",
        value=(
            f"**Advancing**\n`{positive}`\n\n"
            f"**Declining**\n`{negative}`\n\n"
            f"**Unchanged**\n`{unchanged}`\n\n"
            f"**Average 24H**\n`{average_change:+.2f}%`"
        ),
        inline=True,
    )
    embed.add_field(
        name="⌘ RADAR STATUS",
        value=(
            f"**24H Volume**\n`{format_volume(total_volume)}`\n\n"
            f"**Providers**\n`{' / '.join(providers) or 'unavailable'}`\n\n"
            "**Catalog**\n`services.assets`\n\n"
            "**Market Engine**\n`services.market`"
        ),
        inline=True,
    )
    embed.set_footer(text="VEYL • MARKET RADAR • LIVE 24H DATA")

    return embed


def unavailable_embed():
    return discord.Embed(
        title="⌘ VEYL // MARKET RADAR",
        description=(
            "```text\n"
            "MARKET RADAR\n"
            "────────────────────────────────\n"
            "STATUS      DATA UNAVAILABLE\n"
            "────────────────────────────────\n"
            "```\n"
            "VEYL could not retrieve enough market data to build the radar. "
            "Please try again shortly."
        ),
        color=discord.Color.red(),
    )


class VeylRadar(commands.Cog):
    """Scan the shared VEYL asset universe for 24-hour momentum."""

    def __init__(self, bot):
        self.bot = bot
        print("📡 VEYL Market Radar activated.")

    @app_commands.command(
        name="radar",
        description="Scan VEYL assets for 24H market momentum.",
    )
    async def radar(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            market_data = await asyncio.wait_for(
                get_market_data(),
                timeout=RADAR_TIMEOUT,
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                embed=unavailable_embed(),
                ephemeral=True,
            )
            return
        except Exception as error:
            print(
                "[VEYL RADAR] Market data error: "
                f"{type(error).__name__}: {error}"
            )
            await interaction.followup.send(
                embed=unavailable_embed(),
                ephemeral=True,
            )
            return

        by_id = {
            item.get("id"): item
            for item in market_data or []
            if isinstance(item, dict)
        }
        snapshots = []

        for asset in PREDICT_ASSETS:
            item = by_id.get(asset.coin_id)
            if item is None:
                continue

            price = as_float(item.get("usd", item.get("price")))
            change = as_float(item.get("24h_change"))
            volume = as_float(item.get("24h_volume"))

            if price is None or change is None:
                continue

            snapshots.append(
                {
                    "symbol": asset.symbol,
                    "price": price,
                    "change": change,
                    "volume": volume,
                    "provider": item.get("provider"),
                }
            )

        if not snapshots:
            await interaction.followup.send(
                embed=unavailable_embed(),
                ephemeral=True,
            )
            return

        await interaction.followup.send(embed=build_radar_embed(snapshots))


async def setup(bot):
    await bot.add_cog(VeylRadar(bot))
    print("   ✅ commands.radar")
