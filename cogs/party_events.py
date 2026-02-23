import discord
from discord.ext import commands

import db
from utils.party_embed import build_party_embed

MAX_REACTIONS = 4


class PartyEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name != "✅":
            return

        data = db.get_party_by_message(payload.message_id)
        if not data:
            return

        (_, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts) = data
        channel = self.bot.get_channel(channel_id)
        msg = await channel.fetch_message(payload.message_id)

        reaction = discord.utils.get(msg.reactions, emoji="✅")
        users = [u async for u in reaction.users() if not u.bot]

        if len(users) > MAX_REACTIONS:
            await msg.remove_reaction("✅", payload.member)
            await payload.member.send("❌ Party cheia (4/4).")
            return

        creator = msg.guild.get_member(creator_id)
        members = [creator.mention] + [u.mention for u in users]
        embed = build_party_embed(reason_pt, reason_en, start_ts, end_ts, creator, members)
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.emoji.name != "✅":
            return

        data = db.get_party_by_message(payload.message_id)
        if not data:
            return

        (_, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts) = data
        channel = self.bot.get_channel(channel_id)
        msg = await channel.fetch_message(payload.message_id)

        reaction = discord.utils.get(msg.reactions, emoji="✅")
        users = [u async for u in reaction.users() if not u.bot]

        creator = msg.guild.get_member(creator_id)
        members = [creator.mention] + [u.mention for u in users]
        embed = build_party_embed(reason_pt, reason_en, start_ts, end_ts, creator, members)
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(PartyEvents(bot))
