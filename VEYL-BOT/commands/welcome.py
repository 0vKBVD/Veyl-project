import discord
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

WELCOME_CHANNEL_ID = 1542891891471810601


# ============================================================
# WELCOME COG
# ============================================================

class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):

        try:

            channel = self.bot.get_channel(
                WELCOME_CHANNEL_ID
            )

            # Si le salon n'est pas dans le cache
            if channel is None:

                channel = await self.bot.fetch_channel(
                    WELCOME_CHANNEL_ID
                )

            # =================================================
            # EMBED
            # =================================================

            embed = discord.Embed(
                title="🟢  NEW MEMBER",
                description=(
                    f"Welcome {member.mention} to **VEYL**.\n\n"
                    "Enjoy the community and stay updated."
                ),
                color=discord.Color.green()
            )

            # Avatar
            if member.display_avatar:

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

            # Informations
            embed.add_field(
                name="MEMBER",
                value=f"**{member.name}**",
                inline=True
            )

            embed.add_field(
                name="MEMBERS",
                value=f"**{member.guild.member_count}**",
                inline=True
            )

            embed.set_footer(
                text="VEYL • Welcome to the community"
            )

            # =================================================
            # ENVOI
            # =================================================

            await channel.send(
                embed=embed
            )

            print(
                f"👋 Welcome envoyé pour {member}"
            )

        except discord.Forbidden:

            print(
                "❌ VEYL n'a pas la permission "
                "d'envoyer des messages dans le salon entries."
            )

        except discord.NotFound:

            print(
                "❌ Salon entries introuvable."
            )

        except Exception as error:

            print(
                f"❌ Erreur Welcome : {error}"
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Welcome(bot)
    )

    print(
        "👋 Welcome system activé."
    )