import discord
import pytz
import logging
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, time

import db

WINDOW_DAYS = 7
MIN_PERCENT = 80
MAX_T4_ABSENCES = 1

TAG_PT = 1449177142645620807
TAG_EN = 1449177196370460722

TYPE_EMOJI = {
    "T3": "🟦",
    "T4": "🟥",
    "ABYSS": "🟪",
}

TEXTS = {
    "PT": {
        "eligible": (
            "✅ **Elegível para requerimento de item**\n\n"
            "📊 Participação: {percent}%\n"
            "🟢 Presenças: {presences}\n"
            "🔴 Total rotações: {total}"
        ),
        "not_eligible": (
            "❌ **Você não está elegível para requerimento de item**\n\n"
            "📊 **Resumo (últimos {days} dias)**\n"
            "- Presenças: {presences}\n"
            "- Total rotações: {total}\n"
            "- Participação: {percent}%\n"
            "- Faltas em T4: {t4_absences}\n\n"
            "📌 **Motivos:**\n{reasons}"
        ),
    },
    "EN": {
        "eligible": (
            "✅ **Eligible for item request**\n\n"
            "📊 Participation: {percent}%\n"
            "🟢 Presences: {presences}\n"
            "🔴 Total rotations: {total}"
        ),
        "not_eligible": (
            "❌ **You are not eligible for item request**\n\n"
            "📊 **Summary (last {days} days)**\n"
            "- Presences: {presences}\n"
            "- Total rotations: {total}\n"
            "- Participation: {percent}%\n"
            "- T4 absences: {t4_absences}\n\n"
            "📌 **Reasons:**\n{reasons}"
        ),
    },
}


class RotationEligibility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_duplicates.start()

    def cog_unload(self):
        self.cleanup_duplicates.cancel()

    # =========================
    # HELPERS (ORIGINAIS)
    # =========================

    def is_staff(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_guild

    def parse_day(self, day: int) -> bool:
        try:
            datetime.strptime(str(day), "%Y%m%d")
            return True
        except ValueError:
            return False

    def parse_mentions(self, raw: str) -> list[int]:
        ids = set()
        for part in raw.split():
            if part.startswith("<@") and part.endswith(">"):
                ids.add(int(part.strip("<@!>")))
        return list(ids)

    def format_day(self, day: int) -> str:
        return datetime.strptime(str(day), "%Y%m%d").strftime("%d/%m/%Y")

    def get_thread_language(self, thread: discord.Thread) -> str:
        tag_ids = {t.id for t in thread.applied_tags}
        if TAG_EN in tag_ids:
            return "EN"
        return "PT"

    # =========================
    # CORE (MELHORIA AQUI)
    # =========================

    async def _run_eligibility_check(
        self,
        thread: discord.Thread,
        jogador: discord.Member,
        language: str,
    ):
        until = datetime.utcnow()
        since = until - timedelta(days=WINDOW_DAYS)

        stats = db.get_participation_stats(
            jogador.id,
            since.strftime("%Y%m%d"),
            until.strftime("%Y%m%d"),
        )

        total = stats["total_rotations"]
        presences = stats["presences"]
        t4_absences = stats["t4_absences"]

        percent = 100 if total == 0 else int((presences / total) * 100)

        eligible = True
        reasons = []

        if percent < MIN_PERCENT:
            eligible = False
            reasons.append(
                f"- Participação abaixo de {MIN_PERCENT}% ({percent}%)"
                if language == "PT"
                else f"- Participation below {MIN_PERCENT}% ({percent}%)"
            )

        if t4_absences > MAX_T4_ABSENCES:
            eligible = False
            reasons.append(
                "- Faltou 2 ou mais rotações T4"
                if language == "PT"
                else "- Missed 2 or more T4 rotations"
            )

        # 🔥 HISTÓRICO (NOVO, SEM QUEBRAR NADA)
        history = db.get_rotation_history(
            jogador.id,
            int(since.strftime("%Y%m%d")),
            int(until.strftime("%Y%m%d")),
        )

        pres_list = []
        abs_list = []

        for h in history:
            emoji = TYPE_EMOJI.get(h["type"], "⬜")
            line = f"{emoji} {self.format_day(h['day'])} — {h['type']}"
            if h["present"]:
                pres_list.append(line)
            else:
                abs_list.append(line)

        if language == "PT":
            history_block = (
                "\n\n📅 **Histórico de rotações**\n\n"
                "🟢 **Presenças:**\n"
                + ("\n".join(pres_list) if pres_list else "• Nenhuma")
                + "\n\n🔴 **Faltas:**\n"
                + ("\n".join(abs_list) if abs_list else "• Nenhuma")
            )
        else:
            history_block = (
                "\n\n📅 **Rotation history**\n\n"
                "🟢 **Presences:**\n"
                + ("\n".join(pres_list) if pres_list else "• None")
                + "\n\n🔴 **Absences:**\n"
                + ("\n".join(abs_list) if abs_list else "• None")
            )

        texts = TEXTS[language]

        if eligible:
            await thread.send(
                f"{jogador.mention}\n\n" +
                texts["eligible"].format(
                    percent=percent,
                    presences=presences,
                    total=total,
                )
                + history_block
            )
            return

        msg = texts["not_eligible"].format(
            days=WINDOW_DAYS,
            presences=presences,
            total=total,
            percent=percent,
            t4_absences=t4_absences,
            reasons="\n".join(reasons),
        )

        await thread.send(
            f"{jogador.mention}\n\n"
            f"{msg}\n\n"
            f"{history_block}"
        )

        if not thread.archived:
            await thread.edit(archived=True, locked=True)

    # =========================
    # COMANDOS (INTOCADOS)
    # =========================

    @app_commands.command(name="verificar_elegibilidade")
    async def verificar_elegibilidade(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member,
    ):
        if not self.is_staff(interaction):
            return await interaction.response.send_message(
                "Comando exclusivo da staff.", ephemeral=True
            )

        if not isinstance(interaction.channel, discord.Thread):
            return await interaction.response.send_message(
                "Este comando deve ser usado dentro de uma thread.", ephemeral=True
            )

        await interaction.response.defer()
        await self._run_eligibility_check(
            interaction.channel,
            jogador,
            "PT",
        )

    @app_commands.command(name="registrar_rotacao")
    async def registrar_rotacao(
        self,
        interaction: discord.Interaction,
        tipo: str,
        dia: int,
        jogadores: str,
    ):
        if not self.is_staff(interaction):
            return await interaction.response.send_message(
                "Comando exclusivo da staff.", ephemeral=True
            )

        tipo = tipo.upper()
        if tipo not in ("T3", "T4", "ABYSS"):
            return await interaction.response.send_message(
                "Tipo inválido.", ephemeral=True
            )

        if not self.parse_day(dia):
            return await interaction.response.send_message(
                "Data inválida.", ephemeral=True
            )

        ids = self.parse_mentions(jogadores)
        if not ids:
            return await interaction.response.send_message(
                "Mencione ao menos um jogador.", ephemeral=True
            )

        rotation_id = db.get_or_create_rotation(tipo, dia)

        added = 0
        ignored = 0
        for discord_id in ids:
            if db.add_participation(rotation_id, discord_id):
                added += 1
            else:
                ignored += 1

        await interaction.response.send_message(
            f"✅ Rotação **{tipo}** `{dia}` processada\n"
            f"➕ Adicionados: **{added}**\n"
            f"⛔ Ignorados: **{ignored}**",
            ephemeral=True,
        )

    # =========================
    # AUTOMÁTICO VIA TAG (INTOCADO)
    # =========================

    # @commands.Cog.listener()
    # async def on_thread_create(self, thread: discord.Thread):
    #     # Só fórum
    #     if not isinstance(thread.parent, discord.ForumChannel):
    #         return
        
    #     await asyncio.sleep(180)

    #     # Ignora se já arquivado
    #     if thread.archived or thread.locked:
    #         return

    #     tag_ids = {t.id for t in thread.applied_tags}

    #     has_pt = TAG_PT in tag_ids
    #     has_en = TAG_EN in tag_ids

    #     # Nenhuma tag válida
    #     if not has_pt and not has_en:
    #         return

    #     jogador = thread.owner
    #     if not jogador:
    #         return

    #     # Regra de idioma
    #     language = "EN" if has_en else "PT"

    #     await self._run_eligibility_check(
    #         thread=thread,
    #         jogador=jogador,
    #         language=language,
    #     )

    # =========================
    # CLEANUP (INTOCADO)
    # =========================

    @tasks.loop(time=time(hour=6, minute=0, tzinfo=pytz.timezone("America/Sao_Paulo")))
    async def cleanup_duplicates(self):
        try:
            before = db.cursor.execute(
                "SELECT COUNT(*) FROM boss_participation"
            ).fetchone()[0]

            db.cursor.execute("""
                DELETE FROM boss_participation
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM boss_participation
                    GROUP BY rotation_id, discord_id
                )
            """)
            db.conn.commit()

            after = db.cursor.execute(
                "SELECT COUNT(*) FROM boss_participation"
            ).fetchone()[0]

            removed = before - after
            if removed > 0:
                logging.getLogger("bot.commands").info(
                    "[CLEANUP] removidos %s duplicados", removed
                )

        except Exception:
            logging.getLogger("bot.commands").exception(
                "[CLEANUP] erro ao limpar duplicados"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(RotationEligibility(bot))
