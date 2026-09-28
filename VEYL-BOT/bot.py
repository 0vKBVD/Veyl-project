import os
import sys
import asyncio
import traceback

from dotenv import load_dotenv

import discord
from discord.ext import commands


# ============================================================
# VEYL BOT
# CORE SYSTEM
# ============================================================

# Load the local .env file when present. Environment variables already
# exported by the OS still take precedence.
load_dotenv(override=True)

VERSION = "5.1"

COMMANDS_FOLDER = "commands"


# ============================================================
# VEYL TERMINAL
# ============================================================

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

WHITE = "\033[97m"
GREY = "\033[90m"


# ============================================================
# TERMINAL HELPERS
# ============================================================

def clear_terminal():

    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def hide_cursor():

    print(
        "\033[?25l",
        end=""
    )


def show_cursor():

    print(
        "\033[?25h",
        end=""
    )


# ============================================================
# VEYL LOGO
# ============================================================

VEYL_LOGO = r"""
██╗   ██╗███████╗██╗   ██╗██╗
██║   ██║██╔════╝╚██╗ ██╔╝██║
██║   ██║█████╗   ╚████╔╝ ██║
╚██╗ ██╔╝██╔══╝    ╚██╔╝  ██║
 ╚████╔╝ ███████╗   ██║   ███████╗
  ╚═══╝  ╚══════╝   ╚═╝   ╚══════╝
"""


# ============================================================
# STARTUP SCREEN
# ============================================================

def print_startup_screen(
    status="INITIALIZING",
    progress=0,
    active_module=None
):

    clear_terminal()

    print()
    print(
        f"{WHITE}{BOLD}"
    )

    print(
        VEYL_LOGO
    )

    print(
        f"{RESET}"
    )

    print(
        f"                         {BOLD}⌘{RESET}"
    )

    print()

    print(
        f"{BOLD}                    V E Y L{RESET}"
    )

    print(
        f"{DIM}"
        "              MARKET INTELLIGENCE SYSTEM"
        f"{RESET}"
    )

    print()

    print(
        f"{GREY}"
        "    ──────────────────────────────────────────────────────"
        f"{RESET}"
    )

    print()

    print(
        f"    {BOLD}SYSTEM{RESET}"
        f"       {WHITE}{status:<18}{RESET}"
    )

    print(
        f"    {BOLD}VERSION{RESET}"
        f"      {WHITE}{VERSION:<18}{RESET}"
    )

    if active_module:

        print(
            f"    {BOLD}MODULE{RESET}"
            f"       {WHITE}{active_module:<18}{RESET}"
        )

    else:

        print(
            f"    {BOLD}MODULE{RESET}"
            f"       {GREY}{'—':<18}{RESET}"
        )

    print()

    bar_length = 34

    filled = int(
        bar_length * progress / 100
    )

    empty = (
        bar_length
        - filled
    )

    bar = (
        "█" * filled
        + "░" * empty
    )

    print(
        f"    [{bar}] {progress:>3}%"
    )

    print()

    print(
        f"{GREY}"
        "    ──────────────────────────────────────────────────────"
        f"{RESET}"
    )

    print()

    print(
        f"    {DIM}"
        "VEYL CORE • MARKET DATA • INTELLIGENCE • AUTOMATION"
        f"{RESET}"
    )

    print()


# ============================================================
# STARTUP ANIMATION
# ============================================================

async def startup_animation():

    hide_cursor()

    try:

        startup_steps = [

            (
                "BOOTING",
                8,
                "VEYL CORE"
            ),

            (
                "INITIALIZING",
                18,
                "SYSTEM"
            ),

            (
                "LOADING",
                30,
                "MARKET ENGINE"
            ),

            (
                "LOADING",
                43,
                "CASCADE ENGINE"
            ),

            (
                "LOADING",
                56,
                "INTELLIGENCE"
            ),

            (
                "LOADING",
                68,
                "AUTOMATION"
            ),

            (
                "LOADING",
                77,
                "PROFILE ENGINE"
            ),

            (
                "LOADING",
                84,
                "XP ENGINE"
            ),

            (
                "LOADING",
                91,
                "COMMAND SYSTEM"
            ),

            (
                "CONNECTING",
                97,
                "DISCORD"
            ),

        ]

        for (
            status,
            progress,
            module
        ) in startup_steps:

            print_startup_screen(
                status=status,
                progress=progress,
                active_module=module
            )

            await asyncio.sleep(
                0.25
            )

        print_startup_screen(
            status="ONLINE",
            progress=100,
            active_module="VEYL CORE"
        )

        await asyncio.sleep(
            0.7
        )

    finally:

        show_cursor()


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True


# ============================================================
# VEYL BOT CLASS
# ============================================================

class VeylBot(commands.Bot):

    def __init__(self):

        super().__init__(

            command_prefix="!",

            intents=intents,

            help_command=None

        )

        self.loaded_extensions = []

        self.failed_extensions = []

        self.synced_commands = []


    # ========================================================
    # SETUP HOOK
    # ========================================================

    async def setup_hook(self):

        print()

        print(
            f"{WHITE}{BOLD}"
            "◈ VEYL / CORE"
            f"{RESET}"
        )

        print(
            f"{GREY}"
            "Loading command modules..."
            f"{RESET}"
        )

        print()

        # ----------------------------------------------------
        # CHECK COMMANDS DIRECTORY
        # ----------------------------------------------------

        if not os.path.isdir(
            COMMANDS_FOLDER
        ):

            print(
                "❌ commands/ folder not found."
            )

            return

        # ----------------------------------------------------
        # FIND EXTENSIONS
        # ----------------------------------------------------

        extensions = []

        for filename in os.listdir(
            COMMANDS_FOLDER
        ):

            if not filename.endswith(
                ".py"
            ):

                continue

            if filename.startswith(
                "_"
            ):

                continue

            module_name = (
                f"{COMMANDS_FOLDER}."
                f"{filename[:-3]}"
            )

            extensions.append(
                module_name
            )

        extensions.sort()

        # ----------------------------------------------------
        # LOAD EXTENSIONS
        # ----------------------------------------------------

        for extension in extensions:

            try:

                await self.load_extension(
                    extension
                )

                self.loaded_extensions.append(
                    extension
                )

                print(
                    f"   {WHITE}✓{RESET} "
                    f"{extension}"
                )

            except Exception as error:

                self.failed_extensions.append(
                    extension
                )

                print(
                    f"   {GREY}✕{RESET} "
                    f"{extension}"
                )

                print(
                    f"      {GREY}"
                    f"{type(error).__name__}: "
                    f"{error}"
                    f"{RESET}"
                )

                traceback.print_exc()

        # ----------------------------------------------------
        # SYNC
        # ----------------------------------------------------

        print()

        print(
            f"{WHITE}{BOLD}"
            "Synchronizing slash commands..."
            f"{RESET}"
        )

        try:

            synced = await self.tree.sync()

            self.synced_commands = synced

            print(
                f"   {WHITE}✓{RESET} "
                f"{len(synced)} "
                f"slash commands synchronized."
            )

            # ------------------------------------------------
            # DISPLAY COMMANDS
            # ------------------------------------------------

            if synced:

                print()

                print(
                    f"{GREY}"
                    "   ◈ REGISTERED COMMANDS"
                    f"{RESET}"
                )

                for command in sorted(
                    synced,
                    key=lambda cmd: cmd.name
                ):

                    print(
                        f"      {WHITE}/{command.name}"
                        f"{RESET}"
                    )

        except Exception as error:

            print(
                f"   {GREY}✕{RESET} "
                "Slash command synchronization failed."
            )

            print(
                f"      {GREY}"
                f"{type(error).__name__}: "
                f"{error}"
                f"{RESET}"
            )

            traceback.print_exc()


# ============================================================
# BOT INSTANCE
# ============================================================

bot = VeylBot()


# ============================================================
# XP SYSTEM
# ============================================================

@bot.event
async def on_interaction(
    interaction: discord.Interaction
):

    # --------------------------------------------------------
    # Only track slash/application commands.
    # --------------------------------------------------------

    if (
        interaction.type
        != discord.InteractionType.application_command
    ):

        return

    # --------------------------------------------------------
    # Ignore bots.
    # --------------------------------------------------------

    if interaction.user.bot:

        return

    try:

        from services.user_data import (
            track_command
        )

        result = track_command(
            interaction.user.id,
            xp_amount=10
        )

        # ----------------------------------------------------
        # LEVEL UP
        # ----------------------------------------------------

        if result.get(
            "level_up",
            False
        ):

            print()

            print(
                f"{WHITE}{BOLD}"
                "⭐ VEYL LEVEL UP"
                f"{RESET}"
            )

            print(
                f"   User: "
                f"{interaction.user}"
            )

            print(
                f"   Level: "
                f"{result['new_level']}"
            )

            print(
                f"   XP: "
                f"{result['xp']}"
            )

            print()

    except Exception as error:

        print(
            f"{GREY}"
            f"⚠️ VEYL XP tracking error: "
            f"{type(error).__name__}: {error}"
            f"{RESET}"
        )


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print()

    print(
        f"{WHITE}{BOLD}"
        "╔══════════════════════════════════════════════════════╗"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        "║                 VEYL SYSTEM ONLINE                  ║"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        "╚══════════════════════════════════════════════════════╝"
        f"{RESET}"
    )

    print()

    print(
        f"   {BOLD}USER{RESET}"
        f"       {bot.user}"
    )

    print(
        f"   {BOLD}ID{RESET}"
        f"         {bot.user.id}"
    )

    print(
        f"   {BOLD}SERVERS{RESET}"
        f"     {len(bot.guilds)}"
    )

    print(
        f"   {BOLD}MODULES{RESET}"
        f"     {len(bot.loaded_extensions)}"
    )

    print(
        f"   {BOLD}COMMANDS{RESET}"
        f"    {len(bot.tree.get_commands())}"
    )

    print()

    # --------------------------------------------------------
    # ACTIVE MODULES
    # --------------------------------------------------------

    print(
        f"{WHITE}{BOLD}"
        "◈ ACTIVE MODULES"
        f"{RESET}"
    )

    for extension in bot.loaded_extensions:

        print(
            f"   {WHITE}✓{RESET} "
            f"{extension}"
        )

    # --------------------------------------------------------
    # FAILED MODULES
    # --------------------------------------------------------

    if bot.failed_extensions:

        print()

        print(
            f"{GREY}"
            "◈ MODULES WITH ERRORS"
            f"{RESET}"
        )

        for extension in bot.failed_extensions:

            print(
                f"   {GREY}✕{RESET} "
                f"{extension}"
            )

    print()

    print(
        f"{GREY}"
        "VEYL • MARKET INTELLIGENCE • "
        "REAL-TIME SYSTEM"
        f"{RESET}"
    )

    print()


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print()

    print(
        f"{GREY}"
        f"⚠️ VEYL event error • {event}"
        f"{RESET}"
    )

    traceback.print_exc()


# ============================================================
# MAIN
# ============================================================

async def main():

    await startup_animation()

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    token = (
        os.getenv("VEYL_TOKEN")
        or os.getenv("DISCORD_TOKEN")
    )

    if not token:

        print()

        print(
            f"{GREY}"
            "❌ Discord bot token is missing. Set VEYL_TOKEN (or DISCORD_TOKEN) in .env/environment."
            f"{RESET}"
        )

        print()

        return

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    try:

        await bot.start(
            token
        )

    except discord.LoginFailure:

        print()

        print(
            f"{GREY}"
            "❌ VEYL authentication failed."
            f"{RESET}"
        )

    except discord.PrivilegedIntentsRequired:

        print()

        print(
            f"{GREY}"
            "❌ VEYL requires a privileged intent "
            "enabled in the Discord Developer Portal."
            f"{RESET}"
        )

    except Exception as error:

        print()

        print(
            f"{GREY}"
            f"❌ VEYL fatal error: "
            f"{type(error).__name__}: {error}"
            f"{RESET}"
        )

        traceback.print_exc()

    finally:

        if not bot.is_closed():

            await bot.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()

        print(
            f"{GREY}"
            "◈ VEYL shutdown requested."
            f"{RESET}"
        )

        print(
            f"{GREY}"
            "VEYL offline."
            f"{RESET}"
        )

        print()

    finally:

        show_cursor()