import discord
from discord.ext import commands


class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        print(
            "🛠️ VEYL Utility activé."
        )


async def setup(bot):

    await bot.add_cog(
        Utility(bot)
    )

    print(
        "   ✅ commands.utility"
    )