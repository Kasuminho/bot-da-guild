import datetime

from discord.ext import commands, tasks

import db


class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_update.start()

    @tasks.loop(time=datetime.time(hour=12, minute=0))
    async def weekly_update(self):
        if datetime.datetime.utcnow().weekday() != 0:
            return

        players = db.get_all_players()

        for p in players:
            channel = self.bot.get_channel(p[4])
            if channel:
                await channel.send("📌 Lembrete semanal: envie sua atualização.")


async def setup(bot):
    await bot.add_cog(Scheduler(bot))
