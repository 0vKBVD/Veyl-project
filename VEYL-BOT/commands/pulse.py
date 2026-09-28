import json
import os
import asyncio

import discord
from discord import app_commands
from discord.ext import commands, tasks

from services.market import get_crypto_price_async


# ============================================================
# VEYL PULSE
# ============================================================

ALERTS_FILE = "pulse_alerts.json"

CHECK_INTERVAL = 30


# ============================================================
# FILE SYSTEM
# ============================================================

def get_alerts_file():

    return os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        ),
        ALERTS_FILE
    )


# ============================================================
# LOAD ALERTS
# ============================================================

def load_alerts():

    file_path = get_alerts_file()

    if not os.path.exists(file_path):
        return []

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        print(
            "⚠️ Pulse : fichier d'alertes invalide."
        )

    except json.JSONDecodeError:

        print(
            "⚠️ Pulse : pulse_alerts.json est invalide."
        )

    except Exception as error:

        print(
            f"❌ Pulse : impossible de charger les alertes : "
            f"{error}"
        )

    return []


# ============================================================
# SAVE ALERTS
# ============================================================

def save_alerts(alerts):

    file_path = get_alerts_file()

    try:

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                alerts,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            f"❌ Pulse : impossible de sauvegarder les alertes : "
            f"{error}"
        )


# ============================================================
# VEYL PULSE COG
# ============================================================

class VeylPulse(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.alerts = load_alerts()

        print(
            f"⚡ VEYL Pulse activé."
        )

        print(
            f"   ├─ Alertes chargées : {len(self.alerts)}"
        )

        print(
            f"   └─ Check interval : {CHECK_INTERVAL}s"
        )

        self.check_alerts.start()

    # ========================================================
    # UNLOAD
    # ========================================================

    def cog_unload(self):

        self.check_alerts.cancel()

    # ========================================================
    # /ALERT
    # ========================================================

    @app_commands.command(
        name="alert",
        description="Create a VEYL Pulse price alert."
    )
    @app_commands.describe(
        crypto="Crypto ID, e.g. bitcoin or solana",
        price="Target price in USD"
    )
    async def alert(
        self,
        interaction: discord.Interaction,
        crypto: str,
        price: float
    ):

        crypto = crypto.strip().lower()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not crypto:

            await interaction.response.send_message(
                "❌ Please enter a cryptocurrency.",
                ephemeral=True
            )

            return

        if price <= 0:

            await interaction.response.send_message(
                "❌ The target price must be greater than **$0**.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # DEFER
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # GET CURRENT PRICE
        # ----------------------------------------------------

        try:

            data = await get_crypto_price_async(
                crypto
            )

        except Exception as error:

            print(
                f"❌ Pulse price error : {error}"
            )

            data = None

        if not data:

            await interaction.followup.send(
                (
                    f"❌ VEYL could not retrieve market data "
                    f"for **{crypto.upper()}**.\n\n"
                    f"Make sure you're using a valid CoinGecko ID "
                    f"such as `bitcoin`, `ethereum` or `solana`."
                ),
                ephemeral=True
            )

            return

        current_price = data.get(
            "usd"
        )

        if current_price is None:

            await interaction.followup.send(
                "❌ Current price unavailable.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CREATE ALERT
        # ----------------------------------------------------

        alert_data = {

            "user_id": interaction.user.id,

            "crypto": crypto,

            "target_price": float(price),

            "created_price": float(current_price)

        }

        self.alerts.append(
            alert_data
        )

        save_alerts(
            self.alerts
        )

        # ----------------------------------------------------
        # DETERMINE DIRECTION
        # ----------------------------------------------------

        if price >= current_price:

            direction = "ABOVE"

            direction_icon = "📈"

            direction_text = (
                f"when **{crypto.upper()}** reaches "
                f"**${price:,.2f}**"
            )

        else:

            direction = "BELOW"

            direction_icon = "📉"

            direction_text = (
                f"when **{crypto.upper()}** falls to "
                f"**${price:,.2f}**"
            )

        # ----------------------------------------------------
        # EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="⚡ VEYL PULSE",
            description=(
                f"Price alert successfully created.\n\n"
                f"{direction_icon} VEYL will notify you "
                f"{direction_text}."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="ASSET",
            value=f"**{crypto.upper()}**",
            inline=True
        )

        embed.add_field(
            name="CURRENT",
            value=f"**${current_price:,.2f}**",
            inline=True
        )

        embed.add_field(
            name="TARGET",
            value=f"**${price:,.2f}**",
            inline=True
        )

        embed.add_field(
            name="DIRECTION",
            value=f"`{direction}`",
            inline=True
        )

        embed.add_field(
            name="STATUS",
            value="🟢 **ACTIVE**",
            inline=True
        )

        embed.set_footer(
            text="VEYL • Pulse"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

        print(
            f"⚡ Pulse alert created | "
            f"{interaction.user} | "
            f"{crypto.upper()} | "
            f"${price:,.2f} | "
            f"{direction}"
        )

    # ========================================================
    # /ALERTS
    # ========================================================

    @app_commands.command(
        name="alerts",
        description="View your active VEYL Pulse alerts."
    )
    async def alerts(
        self,
        interaction: discord.Interaction
    ):

        user_alerts = [

            alert

            for alert in self.alerts

            if int(
                alert.get("user_id", 0)
            ) == interaction.user.id

        ]

        if not user_alerts:

            await interaction.response.send_message(
                (
                    "⚡ You don't have any active "
                    "VEYL Pulse alerts."
                ),
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="⚡ VEYL PULSE",
            description=(
                f"You have **{len(user_alerts)}** "
                f"active alert(s)."
            ),
            color=discord.Color.blurple()
        )

        for index, alert in enumerate(
            user_alerts,
            start=1
        ):

            crypto = str(
                alert.get(
                    "crypto",
                    "unknown"
                )
            ).upper()

            target = float(
                alert.get(
                    "target_price",
                    0
                )
            )

            created = float(
                alert.get(
                    "created_price",
                    0
                )
            )

            direction = (
                "📈 ABOVE"
                if target >= created
                else "📉 BELOW"
            )

            embed.add_field(
                name=(
                    f"#{index}  •  {crypto}"
                ),
                value=(
                    f"Target: **${target:,.2f}**\n"
                    f"Created: **${created:,.2f}**\n"
                    f"Direction: `{direction}`\n"
                    f"Status: 🟢 **ACTIVE**"
                ),
                inline=False
            )

        embed.set_footer(
            text=(
                "VEYL • Pulse • "
                "/alertremove to remove an alert"
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # /ALERTREMOVE
    # ========================================================

    @app_commands.command(
        name="alertremove",
        description="Remove one of your VEYL Pulse alerts."
    )
    @app_commands.describe(
        alert_id="Alert number shown in /alerts"
    )
    async def alertremove(
        self,
        interaction: discord.Interaction,
        alert_id: int
    ):

        user_alerts = [

            alert

            for alert in self.alerts

            if int(
                alert.get("user_id", 0)
            ) == interaction.user.id

        ]

        if not user_alerts:

            await interaction.response.send_message(
                "⚡ You don't have any active alerts.",
                ephemeral=True
            )

            return

        if (
            alert_id < 1
            or alert_id > len(user_alerts)
        ):

            await interaction.response.send_message(
                (
                    f"❌ Invalid alert ID.\n"
                    f"Choose a number between "
                    f"**1** and **{len(user_alerts)}**."
                ),
                ephemeral=True
            )

            return

        selected_alert = user_alerts[
            alert_id - 1
        ]

        if selected_alert in self.alerts:

            self.alerts.remove(
                selected_alert
            )

        save_alerts(
            self.alerts
        )

        crypto = str(
            selected_alert.get(
                "crypto",
                "unknown"
            )
        ).upper()

        target = float(
            selected_alert.get(
                "target_price",
                0
            )
        )

        embed = discord.Embed(
            title="⚡ VEYL PULSE",
            description=(
                f"Alert **#{alert_id}** has been removed."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="ASSET",
            value=f"**{crypto}**",
            inline=True
        )

        embed.add_field(
            name="TARGET",
            value=f"**${target:,.2f}**",
            inline=True
        )

        embed.add_field(
            name="STATUS",
            value="🔴 **REMOVED**",
            inline=True
        )

        embed.set_footer(
            text="VEYL • Pulse"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        print(
            f"🗑️ Pulse alert removed | "
            f"{interaction.user} | "
            f"{crypto} | "
            f"#{alert_id}"
        )

    # ========================================================
    # /CLEARALERTS
    # ========================================================

    @app_commands.command(
        name="clearalerts",
        description="Delete all your VEYL Pulse alerts."
    )
    async def clearalerts(
        self,
        interaction: discord.Interaction
    ):

        before = len(
            self.alerts
        )

        self.alerts = [

            alert

            for alert in self.alerts

            if int(
                alert.get("user_id", 0)
            ) != interaction.user.id

        ]

        removed = (
            before
            - len(self.alerts)
        )

        save_alerts(
            self.alerts
        )

        embed = discord.Embed(
            title="⚡ VEYL PULSE",
            description=(
                f"Removed **{removed}** alert(s)."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="STATUS",
            value="🔴 **CLEARED**",
            inline=True
        )

        embed.set_footer(
            text="VEYL • Pulse"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        print(
            f"🗑️ Pulse alerts cleared | "
            f"{interaction.user} | "
            f"{removed} alert(s)"
        )

    # ========================================================
    # CHECK ALERTS
    # ========================================================

    @tasks.loop(
        seconds=CHECK_INTERVAL
    )
    async def check_alerts(self):

        if not self.alerts:
            return

        # ----------------------------------------------------
        # GROUP ALERTS BY CRYPTO
        # ----------------------------------------------------
        #
        # Important :
        # plusieurs alertes sur la même crypto ne doivent
        # pas provoquer plusieurs appels inutiles.
        #
        # market.py possède déjà un cache.
        # ----------------------------------------------------

        cryptos = set()

        for alert in self.alerts:

            crypto = alert.get(
                "crypto"
            )

            if crypto:
                cryptos.add(
                    str(crypto).lower()
                )

        prices = {}

        for crypto in cryptos:

            try:

                data = await get_crypto_price_async(
                    crypto
                )

                if data:

                    current_price = data.get(
                        "usd"
                    )

                    if current_price is not None:

                        prices[crypto] = float(
                            current_price
                        )

            except Exception as error:

                print(
                    f"❌ Pulse price check error "
                    f"({crypto}) : {error}"
                )

            # Petite pause pour éviter de marteler
            # inutilement le service.
            await asyncio.sleep(
                0.05
            )

        # ----------------------------------------------------
        # CHECK EACH ALERT
        # ----------------------------------------------------

        triggered = []

        current_alerts = list(
            self.alerts
        )

        for alert in current_alerts:

            try:

                crypto = str(
                    alert.get(
                        "crypto",
                        ""
                    )
                ).lower()

                if not crypto:
                    continue

                if crypto not in prices:
                    continue

                current_price = prices[
                    crypto
                ]

                target = float(
                    alert.get(
                        "target_price",
                        0
                    )
                )

                created_price = float(
                    alert.get(
                        "created_price",
                        current_price
                    )
                )

                # ------------------------------------------------
                # DIRECTION
                # ------------------------------------------------

                if target >= created_price:

                    should_trigger = (
                        current_price >= target
                    )

                    direction = "ABOVE"

                else:

                    should_trigger = (
                        current_price <= target
                    )

                    direction = "BELOW"

                if not should_trigger:
                    continue

                # ------------------------------------------------
                # GET USER
                # ------------------------------------------------

                user_id = int(
                    alert.get(
                        "user_id"
                    )
                )

                user = self.bot.get_user(
                    user_id
                )

                if user is None:

                    try:

                        user = await self.bot.fetch_user(
                            user_id
                        )

                    except Exception as error:

                        print(
                            f"⚠️ Pulse : impossible "
                            f"de récupérer l'utilisateur "
                            f"{user_id} : {error}"
                        )

                        user = None

                # ------------------------------------------------
                # SEND DM
                # ------------------------------------------------

                if user:

                    embed = discord.Embed(
                        title="⚡ VEYL PULSE",
                        description=(
                            f"Your **{crypto.upper()}** "
                            f"price alert has been triggered."
                        ),
                        color=discord.Color.green()
                    )

                    embed.add_field(
                        name="ASSET",
                        value=f"**{crypto.upper()}**",
                        inline=True
                    )

                    embed.add_field(
                        name="CURRENT",
                        value=(
                            f"**${current_price:,.2f}**"
                        ),
                        inline=True
                    )

                    embed.add_field(
                        name="TARGET",
                        value=(
                            f"**${target:,.2f}**"
                        ),
                        inline=True
                    )

                    embed.add_field(
                        name="DIRECTION",
                        value=f"`{direction}`",
                        inline=True
                    )

                    embed.add_field(
                        name="STATUS",
                        value="🟢 **TRIGGERED**",
                        inline=True
                    )

                    embed.set_footer(
                        text="VEYL • Pulse"
                    )

                    try:

                        await user.send(
                            embed=embed
                        )

                        print(
                            f"⚡ Pulse triggered | "
                            f"{crypto.upper()} | "
                            f"${current_price:,.2f} | "
                            f"user={user_id}"
                        )

                    except discord.Forbidden:

                        print(
                            f"⚠️ Pulse : DM fermé pour "
                            f"{user}."
                        )

                    except discord.HTTPException as error:

                        print(
                            f"⚠️ Pulse DM error : {error}"
                        )

                # ------------------------------------------------
                # REMOVE FROM ACTIVE ALERTS
                # ------------------------------------------------

                triggered.append(
                    alert
                )

            except Exception as error:

                print(
                    f"❌ Pulse alert error : {error}"
                )

        # ----------------------------------------------------
        # REMOVE TRIGGERED
        # ----------------------------------------------------

        if triggered:

            for alert in triggered:

                if alert in self.alerts:

                    self.alerts.remove(
                        alert
                    )

            save_alerts(
                self.alerts
            )

    # ========================================================
    # BEFORE LOOP
    # ========================================================

    @check_alerts.before_loop
    async def before_check_alerts(self):

        await self.bot.wait_until_ready()


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylPulse(bot)
    )

    print(
        "⚡ commands.pulse"
    )