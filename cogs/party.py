import datetime
from zoneinfo import ZoneInfo

import discord
from deep_translator import GoogleTranslator as Translator
from discord import app_commands
from discord.ext import commands

from db import conn, cursor
from utils.party_embed import build_party_embed
from utils.translator import translate_reason
from views.timezone_select import TimezoneView

translator = Translator()


class Party(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="party", description="Criar uma party")
    async def party(
        self,
        interaction: discord.Interaction,
        motivo: str,
        inicio: str,  # YYYY-MM-DD HH:MM
        fim: str,  # HH:MM
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            cursor.execute(
                "SELECT timezone FROM players WHERE discord_id = ?",
                (interaction.user.id,),
            )
            row = cursor.fetchone()

            if not row or not row[0]:
                await interaction.followup.send(
                    "Antes de criar uma party, escolha sua cidade:",
                    view=TimezoneView(),
                    ephemeral=True,
                )
                return

            tz = ZoneInfo(row[0])

            start = datetime.datetime.strptime(inicio, "%Y-%m-%d %H:%M").replace(
                tzinfo=tz
            )

            end = datetime.datetime.strptime(fim, "%H:%M").replace(
                year=start.year, month=start.month, day=start.day, tzinfo=tz
            )
        except ValueError:
            await interaction.followup.send(
                "❌ Formato inválido.\nUse:\n`2025-12-25 20:00` e `22:00`"
            )
            return

        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())

        reason_pt, reason_en = translate_reason(motivo)

        members = [interaction.user.mention]

        embed = build_party_embed(
            reason_pt, reason_en, start_ts, end_ts, interaction.user, members
        )

        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("✅")

        cursor.execute(
            """
            INSERT INTO parties
            (message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg.id,
                msg.channel.id,
                interaction.user.id,
                reason_pt,
                reason_en,
                start_ts,
                end_ts,
            ),
        )
        conn.commit()

        await interaction.followup.send("✅ Party criada com sucesso.")

    @app_commands.command(name="party_delete", description="Apagar sua party")
    async def party_delete(self, interaction: discord.Interaction):
        cursor.execute(
            "SELECT message_id, channel_id FROM parties WHERE creator_id = ?",
            (interaction.user.id,),
        )
        row = cursor.fetchone()

        if not row:
            await interaction.response.send_message(
                "❌ Você não tem party ativa.", ephemeral=True
            )
            return

        message_id, channel_id = row
        channel = self.bot.get_channel(channel_id)
        msg = await channel.fetch_message(message_id)
        await msg.delete()

        cursor.execute("DELETE FROM parties WHERE message_id = ?", (message_id,))
        conn.commit()

        await interaction.response.send_message("🧹 Party apagada.", ephemeral=True)

    @app_commands.command(
        name="party_clear_all", description="STAFF — apagar todas as partys"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def party_clear_all(self, interaction: discord.Interaction):
        cursor.execute("SELECT message_id, channel_id FROM parties")
        rows = cursor.fetchall()

        for message_id, channel_id in rows:
            try:
                channel = self.bot.get_channel(channel_id)
                msg = await channel.fetch_message(message_id)
                await msg.delete()
            except Exception:
                pass

        cursor.execute("DELETE FROM parties")
        conn.commit()

        await interaction.response.send_message(
            "🔥 Todas as partys foram apagadas.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Party(bot))
