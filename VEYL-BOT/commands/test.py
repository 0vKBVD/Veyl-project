import time

import aiohttp
import discord


# ============================================================
# VEYL — SYSTEM DIAGNOSTICS
# ============================================================

BINANCE_URL = "https://api.binance.com/api/v3/ping"


# ============================================================
# STATUS HELPERS
# ============================================================

def status_icon(ok):
    return "🟢" if ok else "🔴"


def status_text(ok):
    return "ONLINE" if ok else "ERROR"


def format_latency(ms):
    if ms < 100:
        return f"{ms:.0f}ms"
    if ms < 300:
        return f"{ms:.0f}ms"
    return f"{ms:.0f}ms"


# ============================================================
# BINANCE CHECK
# ============================================================

async def check_binance():

    start = time.perf_counter()

    try:

        timeout = aiohttp.ClientTimeout(
            total=5
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                BINANCE_URL,
                headers={
                    "accept": "application/json",
                    "user-agent": "VEYL-System-Diagnostics/1.0"
                }
            ) as response:

                latency = (
                    time.perf_counter() - start
                ) * 1000

                if response.status == 200:

                    return True, latency

                return False, latency

    except Exception:

        latency = (
            time.perf_counter() - start
        ) * 1000

        return False, latency


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    @bot.tree.command(
        name="test",
        description="VEYL System Diagnostics — vérifie tous les systèmes."
    )
    async def test(
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        # ====================================================
        # DISCORD
        # ====================================================

        discord_ok = bot.is_ready()

        latency = bot.latency * 1000

        # ====================================================
        # COMMANDS
        # ====================================================

        synced_commands = list(
            bot.tree.get_commands()
        )

        commands_count = len(
            synced_commands
        )

        commands_ok = commands_count > 0

        # ====================================================
        # EXTENSIONS
        # ====================================================

        extensions = bot.extensions

        extensions_count = len(
            extensions
        )

        extensions_ok = extensions_count > 0

        # ====================================================
        # BINANCE
        # ====================================================

        binance_ok, binance_latency = (
            await check_binance()
        )

        # ====================================================
        # GUILDS
        # ====================================================

        servers_count = len(
            bot.guilds
        )

        guilds_ok = servers_count > 0

        # ====================================================
        # AUTOMATION DETECTION
        # ====================================================

        automation_loaded = any(
            "automation" in name.lower()
            for name in extensions
        )

        flow_loaded = any(
            "flow" in name.lower()
            for name in extensions
        )

        pulse_loaded = any(
            "pulse" in name.lower()
            for name in extensions
        )

        terminal_loaded = any(
            "terminal" in name.lower()
            for name in extensions
        )

        price_loaded = any(
            "price" in name.lower()
            for name in extensions
        )

        intelligence_loaded = (
            bot.tree.get_command(
                "intelligence"
            ) is not None
        )

        # ====================================================
        # GLOBAL SYSTEM STATUS
        # ====================================================

        critical_systems = [
            discord_ok,
            commands_ok,
            extensions_ok,
            guilds_ok,
            binance_ok,
            intelligence_loaded
        ]

        all_ok = all(
            critical_systems
        )

        # ====================================================
        # EMBED COLOR
        # ====================================================

        if all_ok:

            embed_color = 0xF2F2F2

        else:

            embed_color = 0x555555

        # ====================================================
        # EMBED
        # ====================================================

        embed = discord.Embed(

            title="◈ VEYL / SYSTEM DIAGNOSTICS",

            description=(
                "```text\n"
                "╔══════════════════════════════════════════╗\n"
                "║             VEYL CORE SYSTEM             ║\n"
                "║          FULL SYSTEM DIAGNOSTICS         ║\n"
                "╚══════════════════════════════════════════╝\n"
                "```\n"
                f"**SYSTEM STATUS**\n"
                f"{status_icon(all_ok)} "
                f"**{status_text(all_ok)}**\n\n"
                f"`VEYL diagnostic scan completed.`"
            ),

            color=embed_color,

            timestamp=discord.utils.utcnow()
        )

        # ====================================================
        # CORE
        # ====================================================

        embed.add_field(

            name="◈ CORE",

            value=(
                f"{status_icon(discord_ok)} "
                f"**Discord Gateway**\n"
                f"`{format_latency(latency)}`\n\n"

                f"{status_icon(guilds_ok)} "
                f"**Server Connection**\n"
                f"`{servers_count} server(s)`\n\n"

                f"{status_icon(commands_ok)} "
                f"**Command System**\n"
                f"`{commands_count} commands`"
            ),

            inline=True
        )

        # ====================================================
        # MARKET DATA
        # ====================================================

        embed.add_field(

            name="◈ MARKET DATA",

            value=(
                f"{status_icon(binance_ok)} "
                f"**Binance API**\n"
                f"`{format_latency(binance_latency)}`\n\n"

                f"{status_icon(price_loaded)} "
                f"**Price Engine**\n"
                f"`{'LOADED' if price_loaded else 'NOT LOADED'}`\n\n"

                f"{status_icon(intelligence_loaded)} "
                f"**Intelligence**\n"
                f"`{'LOADED' if intelligence_loaded else 'NOT LOADED'}`"
            ),

            inline=True
        )

        # ====================================================
        # AUTOMATION
        # ====================================================

        embed.add_field(

            name="◈ AUTOMATION",

            value=(
                f"{status_icon(automation_loaded)} "
                f"**Automation**\n"
                f"`{'ONLINE' if automation_loaded else 'OFFLINE'}`\n\n"

                f"{status_icon(flow_loaded)} "
                f"**Whale Flow**\n"
                f"`{'ONLINE' if flow_loaded else 'OFFLINE'}`\n\n"

                f"{status_icon(pulse_loaded)} "
                f"**Pulse**\n"
                f"`{'ONLINE' if pulse_loaded else 'OFFLINE'}`"
            ),

            inline=True
        )

        # ====================================================
        # TERMINAL
        # ====================================================

        embed.add_field(

            name="◈ TERMINAL",

            value=(
                f"{status_icon(terminal_loaded)} "
                f"**VEYL Terminal PRO**\n"
                f"`{'ONLINE' if terminal_loaded else 'OFFLINE'}`\n\n"

                f"{status_icon(extensions_ok)} "
                f"**Extensions**\n"
                f"`{extensions_count} loaded`\n\n"

                f"{status_icon(commands_ok)} "
                f"**Slash Commands**\n"
                f"`{commands_count} registered`"
            ),

            inline=True
        )

        # ====================================================
        # EXTENSIONS LIST
        # ====================================================

        extension_lines = []

        for extension_name in sorted(
            extensions
        ):

            clean_name = extension_name.replace(
                "commands.",
                ""
            )

            extension_lines.append(
                f"🟢 `{clean_name}`"
            )

        if extension_lines:

            extensions_text = "\n".join(
                extension_lines
            )

            if len(extensions_text) > 1000:

                extensions_text = (
                    "\n".join(
                        extension_lines[:20]
                    )
                    + f"\n`+ "
                    f"{len(extension_lines) - 20} "
                    f"more`"
                )

        else:

            extensions_text = "`NONE`"

        embed.add_field(

            name=(
                f"◈ LOADED SERVICES "
                f"• {extensions_count}"
            ),

            value=extensions_text,

            inline=False
        )

        # ====================================================
        # COMMAND LIST
        # ====================================================

        command_names = sorted(
            command.name
            for command in synced_commands
        )

        if command_names:

            command_text = " ".join(
                f"`/{name}`"
                for name in command_names
            )

            if len(command_text) > 1000:

                command_text = (
                    " ".join(
                        f"`/{name}`"
                        for name in command_names[:25]
                    )
                    + f" `+{len(command_names) - 25}`"
                )

        else:

            command_text = "`NONE`"

        embed.add_field(

            name=(
                f"◈ COMMAND REGISTRY "
                f"• {commands_count}"
            ),

            value=command_text,

            inline=False
        )

        # ====================================================
        # FINAL STATUS
        # ====================================================

        if all_ok:

            final_status = (
                "🟢 **ALL SYSTEMS OPERATIONAL**\n"
                "`VEYL core, market data and services "
                "are responding normally.`"
            )

        else:

            final_status = (
                "🟠 **SYSTEM WARNING**\n"
                "`One or more critical services "
                "require attention.`"
            )

        embed.add_field(

            name="◈ FINAL DIAGNOSTIC",

            value=final_status,

            inline=False
        )

        # ====================================================
        # FOOTER
        # ====================================================

        embed.set_footer(

            text=(
                "VEYL SYSTEM DIAGNOSTICS • "
                "CORE MONITOR • LIVE"
            )
        )

        # ====================================================
        # SEND
        # ====================================================

        await interaction.followup.send(
            embed=embed
        )