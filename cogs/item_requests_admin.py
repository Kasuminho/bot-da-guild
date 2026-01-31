import discord
from discord.ext import commands

from config import ITEM_REQUEST_SUMMARY_CHANNEL_ID, STAFF_ROLE_ID
from cogs.item_requests_scheduler import ItemRequestsScheduler


def is_staff():
    async def predicate(ctx):
        return discord.utils.get(ctx.author.roles, id=STAFF_ROLE_ID) is not None
    return commands.check(predicate)


class ItemRequestsAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="request_summary")
    @is_staff()
    async def request_summary(self, ctx):
        channel = self.bot.get_channel(ITEM_REQUEST_SUMMARY_CHANNEL_ID)
        if not channel:
            await ctx.send("❌ Canal de resumo não encontrado.")
            return

        scheduler = self.bot.get_cog("ItemRequestsScheduler")
        if not scheduler:
            await ctx.send("❌ Scheduler não carregado.")
            return

        await scheduler.send_item_summary()
        await ctx.send("✅ Ranking postado com sucesso.")


async def setup(bot):
    await bot.add_cog(ItemRequestsAdmin(bot))
