import discord


VERIFY_CHANNEL_ID = 1542859318817202176
VERIFIED_ROLE_ID = 1542846789311275169


class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="veyl_verify_button"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            return

        role = interaction.guild.get_role(
            VERIFIED_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Verification role not found.",
                ephemeral=True
            )

            return

        if role in interaction.user.roles:

            await interaction.response.send_message(
                "✅ You are already verified.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.add_roles(
                role,
                reason="VEYL verification"
            )

            await interaction.response.send_message(
                "✅ You are now verified. Welcome to VEYL.",
                ephemeral=True
            )

            print(
                f"✅ {interaction.user} verified."
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ VEYL doesn't have permission to give "
                "the Verified role.",
                ephemeral=True
            )

        except Exception as error:

            print(
                f"❌ Verification error: {error}"
            )

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Something went wrong.",
                    ephemeral=True
                )


async def setup(bot):

    bot.add_view(
        VerifyView()
    )

    channel = bot.get_channel(
        VERIFY_CHANNEL_ID
    )

    if channel is None:

        try:

            channel = await bot.fetch_channel(
                VERIFY_CHANNEL_ID
            )

        except Exception as error:

            print(
                f"❌ Verify channel not found: {error}"
            )

            return

    if not isinstance(
        channel,
        discord.TextChannel
    ):

        print(
            "❌ The Verify channel must be a text channel."
        )

        return

    # Cherche un ancien message VEYL
    existing_message = None

    try:

        async for message in channel.history(
            limit=50
        ):

            if (
                message.author.id == bot.user.id
                and message.components
            ):

                existing_message = message
                break

    except Exception as error:

        print(
            f"❌ Impossible de vérifier les anciens messages: {error}"
        )

    # Si le message existe déjà, on ne crée rien
    if existing_message:

        print(
            "✅ Verify panel already exists."
        )

        return

    # Création du panneau
    try:

        embed = discord.Embed(
            title="✅ VERIFY",
            description=(
                "Welcome to **VEYL**.\n\n"
                "Click the button below to verify your account "
                "and access the server.\n\n"
                "**🔐 Verification required**"
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="VEYL • Verification"
        )

        await channel.send(
            embed=embed,
            view=VerifyView()
        )

        print(
            "✅ Verify panel created."
        )

    except Exception as error:

        print(
            f"❌ Unable to create verify panel: {error}"
        )