import time
import discord
import os
from discord.ext import commands, tasks
from config import (
    ITEM_REQUEST_SUMMARY_CHANNEL_ID
)

from utils.i18n import TEXT
import db

lang = "pt"
ITEM_IMAGES_DIR = "images/itens"


class ItemRequestsScheduler(commands.Cog):
    """
    Scheduler diário para cobrança automática de updates
    e controle de rank dos item requests.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_check.start()
        self.daily_loop.start()

    def cog_unload(self):
        self.daily_check.cancel()
        self.daily_loop.cancel()

    async def clear_summary_channel(self, channel: discord.TextChannel):
        await channel.purge(
            limit=100,
            check=lambda m: m.author == self.bot.user,
            bulk=True
        )

    async def send_item_summary(self):
        channel = self.bot.get_channel(ITEM_REQUEST_SUMMARY_CHANNEL_ID)
        if not channel:
            return

        await self.clear_summary_channel(channel)

        rows = db.get_daily_item_summary()
        if not rows:
            return

        embeds = {}
        files = {}

        for item_name, rank, player, remaining, thread_id in rows:
            if item_name not in embeds:
                embed = discord.Embed(
                    title=TEXT["rank_header"][lang].format(item=item_name),
                    color=discord.Color.blurple()
                )

                image_path = os.path.join(ITEM_IMAGES_DIR, f"{item_name}.png")

                if os.path.isfile(image_path):
                    file = discord.File(image_path, filename=f"{item_name}.png")
                    embed.set_thumbnail(url=f"attachment://{item_name}.png")
                    files[item_name] = file
                else:
                    files[item_name] = None

                embeds[item_name] = embed

            thread = self.bot.get_channel(thread_id)
            thread_link = thread.jump_url if thread else ""

            embeds[item_name].add_field(
                name=f"{rank}º - {player}",
                value=TEXT["rank_line"][lang].format(
                    remaining=remaining,
                    link=thread_link
                ),
                inline=False
            )

        for item_name, embed in embeds.items():
            file = files.get(item_name)
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)

    # ==========================================================
    # TASK DIÁRIA – RANK / WARN
    # ==========================================================

    @tasks.loop(minutes=60)
    async def daily_loop(self):
        await self.bot.wait_until_ready()
        await self.send_item_summary()

    @tasks.loop(hours=24)
    async def daily_check(self):
        await self.bot.wait_until_ready()

        now = time.time()
        requests = db.get_all_item_requests_for_check()

        for req in requests:
            (
                request_id,
                discord_id,
                player_name,
                item_name,
                rank_position,
                thread_id,
                thread_channel_id,
                last_update,
                warned_3d,
                warned_4d,
            ) = req

            if item_name in ("creature of gaiety", "elder dragon isteria", "carnival queen"):
                continue
            
            if rank_position != 1:
                db.fix_last_update(request_id, last_update)
                continue

            # ============================
            # 🔥 FAILSAFE TIMESTAMP
            # ============================

            # Se veio em ms
            if last_update > 10_000_000_000:
                last_update = int(last_update / 1000)
                db.fix_last_update(request_id, last_update)

            # Se veio do futuro
            if last_update > now:
                last_update = int(now)
                db.fix_last_update(request_id, last_update)

            days_idle = int((now - last_update) / 86400)

            thread = self.bot.get_channel(thread_id)
            if not thread:
                continue

            # =====================
            # 3 DIAS
            # =====================
            if days_idle >= 3 and not warned_3d:
                await thread.send(
                    TEXT["idle_3d"][lang].format(player=discord_id, item=item_name)
                )
                db.mark_request_warned(request_id, "warned_3d")
                continue

            # =====================
            # 4 DIAS
            # =====================
            if days_idle >= 4 and not warned_4d:
                await thread.send(
                    TEXT["idle_4d"][lang].format(player=discord_id, item=item_name)
                )
                db.mark_request_warned(request_id, "warned_4d")
                continue

            # =====================
            # 5 DIAS → RANK DOWN
            # =====================
            if days_idle >= 5:
                await thread.send(
                    TEXT["rank_down"][lang].format(player=discord_id, item=item_name)
                )
                db.drop_request_rank(request_id)

    # ==========================================================
    # START LOG
    # ==========================================================

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()
        print("[ItemRequestsScheduler] Scheduler diário iniciado.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ItemRequestsScheduler(bot))
