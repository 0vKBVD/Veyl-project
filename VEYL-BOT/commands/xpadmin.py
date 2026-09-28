import discord
from discord import app_commands
from discord.ext import commands

from services.user_data import (
    get_user,
    add_xp,
    calculate_level,
)


# ============================================================
# 🔐 VEYL OWNER CONFIG
# ============================================================
#
# >>> 1431999599882797096 <<<
#
# Exemple :
# OWNER_ID = 123456789012345678
#
# Pour récupérer ton ID :
# Discord → Paramètres → Avancés → Mode développeur
# Puis clic droit sur ton profil → Copier l'identifiant
#
# ============================================================

OWNER_ID = 1431999599882797096


# ============================================================
# VEYL COLORS
# ============================================================

VEYL_WHITE = 0xF2F2F2
VEYL_GREY = 0x8A8A8A


# ============================================================
# VEYL / XP ADMIN ENGINE
# ============================================================

class VeylXPAdmin(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        print(
            "⚡ VEYL XP Admin Engine activé."
        )


    # ========================================================
    # OWNER CHECK
    # ========================================================

    def is_owner(
        self,
        user_id: int
    ):

        return user_id == OWNER_ID


    # ========================================================
    # /XPADMIN
    # ========================================================

    @app_commands.command(
        name="xpadmin",
        description="VEYL XP administration."
    )

    @app_commands.describe(
        action="XP action to perform.",
        member="Member to modify.",
        amount="Amount of XP."
    )

    @app_commands.choices(
        action=[
            app_commands.Choice(
                name="Add XP",
                value="add"
            ),

            app_commands.Choice(
                name="Remove XP",
                value="remove"
            ),

            app_commands.Choice(
                name="Set XP",
                value="set"
            ),

            app_commands.Choice(
                name="Reset XP",
                value="reset"
            ),
        ]
    )

    async def xpadmin(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        member: discord.Member,
        amount: int | None = None
    ):

        # ====================================================
        # 🔐 OWNER ONLY
        # ====================================================

        if not self.is_owner(
            interaction.user.id
        ):

            embed = discord.Embed(

                title="◈ VEYL / XP ADMIN",

                description=(
                    "### ACCESS DENIED\n\n"
                    "This command is restricted "
                    "to the **VEYL owner**."
                ),

                color=VEYL_WHITE
            )

            embed.set_footer(
                text="VEYL SECURITY • OWNER ONLY"
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # VALIDATE ACTION
        # ====================================================

        if action.value not in (
            "add",
            "remove",
            "set",
            "reset"
        ):

            await interaction.response.send_message(

                "❌ Invalid XP action.",

                ephemeral=True

            )

            return


        # ====================================================
        # AMOUNT REQUIRED
        # ====================================================

        if action.value != "reset":

            if amount is None:

                embed = discord.Embed(

                    title="◈ VEYL / XP ADMIN",

                    description=(
                        "### AMOUNT REQUIRED\n\n"
                        "Please specify an XP amount."
                    ),

                    color=VEYL_WHITE
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

                return


            # =================================================
            # NEGATIVE AMOUNT PROTECTION
            # =================================================

            if amount <= 0:

                embed = discord.Embed(

                    title="◈ VEYL / XP ADMIN",

                    description=(
                        "### INVALID AMOUNT\n\n"
                        "XP amount must be greater than **0**."
                    ),

                    color=VEYL_WHITE
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

                return


        # ====================================================
        # GET USER DATA
        # ====================================================

        user = get_user(
            member.id
        )

        if not user:

            user = {
                "xp": 0
            }


        old_xp = int(
            user.get(
                "xp",
                0
            )
        )

        old_level = calculate_level(
            old_xp
        )


        # ====================================================
        # ADD XP
        # ====================================================

        if action.value == "add":

            add_xp(
                member.id,
                amount
            )

            updated_user = get_user(
                member.id
            )

            new_xp = int(
                updated_user.get(
                    "xp",
                    old_xp + amount
                )
            )

            action_text = (
                f"+{amount:,} XP"
            )


        # ====================================================
        # REMOVE XP
        # ====================================================

        elif action.value == "remove":

            new_xp = max(
                0,
                old_xp - amount
            )

            difference = (
                new_xp - old_xp
            )

            if difference != 0:

                add_xp(
                    member.id,
                    difference
                )

            action_text = (
                f"-{amount:,} XP"
            )


        # ====================================================
        # SET XP
        # ====================================================

        elif action.value == "set":

            new_xp = max(
                0,
                amount
            )

            difference = (
                new_xp - old_xp
            )

            if difference != 0:

                add_xp(
                    member.id,
                    difference
                )

            action_text = (
                f"SET → {new_xp:,} XP"
            )


        # ====================================================
        # RESET XP
        # ====================================================

        else:

            new_xp = 0

            if old_xp != 0:

                add_xp(
                    member.id,
                    -old_xp
                )

            action_text = (
                "RESET → 0 XP"
            )


        # ====================================================
        # FINAL LEVEL
        # ====================================================

        new_level = calculate_level(
            new_xp
        )


        # ====================================================
        # LEVEL CHANGE TEXT
        # ====================================================

        if new_level > old_level:

            level_text = (
                f"🚀 **LEVEL UP**\n"
                f"LEVEL `{old_level}` → "
                f"LEVEL `{new_level}`"
            )

        elif new_level < old_level:

            level_text = (
                f"📉 **LEVEL DOWN**\n"
                f"LEVEL `{old_level}` → "
                f"LEVEL `{new_level}`"
            )

        else:

            level_text = (
                f"LEVEL `{new_level}`"
            )


        # ====================================================
        # SUCCESS EMBED
        # ====================================================

        embed = discord.Embed(

            title="◈ VEYL / XP ADMIN",

            description=(
                "### XP SYSTEM UPDATED\n\n"
                f"**Member**\n"
                f"{member.mention}\n\n"
                f"**Operation**\n"
                f"`{action_text}`"
            ),

            color=VEYL_WHITE
        )


        # ====================================================
        # AVATAR
        # ====================================================

        embed.set_thumbnail(
            url=member.display_avatar.url
        )


        # ====================================================
        # BEFORE
        # ====================================================

        embed.add_field(

            name="BEFORE",

            value=(
                f"**{old_xp:,} XP**\n"
                f"LEVEL `{old_level}`"
            ),

            inline=True
        )


        # ====================================================
        # AFTER
        # ====================================================

        embed.add_field(

            name="AFTER",

            value=(
                f"**{new_xp:,} XP**\n"
                f"LEVEL `{new_level}`"
            ),

            inline=True
        )


        # ====================================================
        # LEVEL STATUS
        # ====================================================

        embed.add_field(

            name="LEVEL STATUS",

            value=level_text,

            inline=False
        )


        # ====================================================
        # XP DIFFERENCE
        # ====================================================

        difference = (
            new_xp - old_xp
        )

        if difference > 0:

            difference_text = (
                f"+{difference:,} XP"
            )

        elif difference < 0:

            difference_text = (
                f"{difference:,} XP"
            )

        else:

            difference_text = (
                "0 XP"
            )


        embed.add_field(

            name="XP CHANGE",

            value=(
                f"`{difference_text}`"
            ),

            inline=True
        )


        # ====================================================
        # EXECUTOR
        # ====================================================

        embed.add_field(

            name="AUTHORIZED BY",

            value=(
                interaction.user.mention
            ),

            inline=True
        )


        # ====================================================
        # FOOTER
        # ====================================================

        embed.set_footer(

            text=(
                "VEYL XP ADMIN • "
                "OWNER CONTROL"
            )

        )


        # ====================================================
        # SEND
        # ====================================================

        await interaction.response.send_message(

            embed=embed,

            ephemeral=True

        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        VeylXPAdmin(bot)
    )

    print(
        "   ✓ commands.xpadmin"
    )