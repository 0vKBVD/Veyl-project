import json
import os

import discord


OWNER_ID = 1431999599882797096
BUG_FORUM_ID = 1542852924835631134

PANEL_FILE = "bug_panel.json"


def load_panel_id():

    if not os.path.exists(PANEL_FILE):
        return None

    try:

        with open(
            PANEL_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data.get("thread_id")

    except Exception:

        return None


def save_panel_id(thread_id):

    with open(
        PANEL_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "thread_id": thread_id
            },
            file,
            indent=4
        )


class BugModal(
    discord.ui.Modal,
    title="Report a Bug"
):

    bug = discord.ui.TextInput(
        label="Describe the bug",
        placeholder="Explain what happened...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        try:

            owner = interaction.client.get_user(
                OWNER_ID
            )

            if owner is None:

                owner = await interaction.client.fetch_user(
                    OWNER_ID
                )

            embed = discord.Embed(
                title="🐛 New VEYL Bug Report",
                color=discord.Color.red()
            )

            embed.add_field(
                name="User",
                value=(
                    f"{interaction.user.mention}\n"
                    f"`{interaction.user}`"
                ),
                inline=False
            )

            embed.add_field(
                name="User ID",
                value=f"`{interaction.user.id}`",
                inline=True
            )

            if interaction.guild:

                embed.add_field(
                    name="Server",
                    value=(
                        f"{interaction.guild.name}\n"
                        f"`{interaction.guild.id}`"
                    ),
                    inline=True
                )

            embed.add_field(
                name="Bug",
                value=self.bug.value,
                inline=False
            )

            embed.set_footer(
                text="VEYL • Bug Reports"
            )

            await owner.send(
                embed=embed
            )

            await interaction.response.send_message(
                "✅ Merci pour votre partage.",
                ephemeral=True
            )

            print(
                f"🐛 Bug report received from "
                f"{interaction.user} "
                f"({interaction.user.id})"
            )

        except Exception as error:

            print(
                f"❌ Bug report error: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Une erreur s'est produite.",
                    ephemeral=True
                )


class BugView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Report a Bug",
        emoji="🐛",
        style=discord.ButtonStyle.danger,
        custom_id="veyl_report_bug"
    )
    async def report_bug(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            BugModal()
        )


async def setup(bot):

    bot.add_view(
        BugView()
    )

    forum = bot.get_channel(
        BUG_FORUM_ID
    )

    if forum is None:

        try:

            forum = await bot.fetch_channel(
                BUG_FORUM_ID
            )

        except Exception as error:

            print(
                f"❌ Impossible de trouver le Forum : {error}"
            )

            return

    if not isinstance(
        forum,
        discord.ForumChannel
    ):

        print(
            "❌ L'ID fourni n'est pas un salon Forum."
        )

        return

    # =====================================================
    # RECUPERATION DU POST EXISTANT
    # =====================================================

    panel_thread_id = load_panel_id()

    existing_thread = None

    if panel_thread_id:

        try:

            existing_thread = await bot.fetch_channel(
                panel_thread_id
            )

        except discord.NotFound:

            existing_thread = None

        except Exception as error:

            print(
                f"⚠️ Impossible de récupérer le panneau : {error}"
            )

    # =====================================================
    # SI LE POST N'EXISTE PLUS → ON EN CREE UN
    # =====================================================

    if existing_thread is None:

        try:

            thread, message = await forum.create_thread(
                name="🐛・Report a Bug",
                content=(
                    "## 🐛 VEYL Bug Reports\n\n"
                    "Found a bug or something that isn't "
                    "working correctly?\n\n"
                    "Click the button below to report it "
                    "directly to the VEYL team.\n\n"
                    "Please provide as much detail as possible."
                ),
                view=BugView()
            )

            save_panel_id(
                thread.id
            )

            print(
                "✅ Bug report panel créé dans le Forum."
            )

        except Exception as error:

            print(
                f"❌ Impossible de créer le post Forum : {error}"
            )

    else:

        print(
            "✅ Bug report panel déjà présent."
        )


    # =====================================================
    # COMMANDE /BUG
    # =====================================================

    @bot.tree.command(
        name="bug",
        description="Open the VEYL bug report form"
    )
    async def bug(
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            BugModal()
        )