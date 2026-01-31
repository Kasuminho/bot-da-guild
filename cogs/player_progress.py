import discord
from discord import app_commands
from discord.ext import commands, tasks

import db


class PlayerProgress(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_loop.start()

    def cog_unload(self):
        self.cleanup_loop.cancel()

    # =========================
    # REGISTRAR LEVEL
    # =========================
    @app_commands.command(
        name="registrarlevel",
        description="Registrar level diário do jogador",
    )
    async def registrarlevel(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member,
        level: int,
        dias_atras: int = 0,
    ):
        if dias_atras < 0 or dias_atras > 3:
            await interaction.response.send_message(
                "❌ Só é permitido até 3 dias retroativos.",
                ephemeral=True,
            )
            return

        try:
            db.add_player_level(jogador.id, jogador.display_name, level, dias_atras)
        except Exception:
            await interaction.response.send_message(
                "⚠️ Esse jogador já tem registro nesse dia.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Level **{level}** registrado para {jogador.mention}.",
            ephemeral=True,
        )

    # =========================
    # CHECAR QUEM ESTÁ PARADO
    # =========================
    @app_commands.command(
        name="checarniveis",
        description="Ver jogadores sem progresso nos últimos 3 dias",
    )
    async def checarniveis(self, interaction: discord.Interaction):
        stuck = db.get_players_stuck_3_days()

        if not stuck:
            await interaction.response.send_message(
                "🚀 Todos estão progredindo!",
                ephemeral=True,
            )
            return

        msg = "⚠️ **Jogadores sem progresso há 3 dias:**\n\n"
        for pid, name in stuck:
            msg += f"• <@{pid}> ({name})\n"

        await interaction.response.send_message(msg, ephemeral=True)

    # =========================
    # LIMPEZA AUTOMÁTICA
    # =========================
    @tasks.loop(hours=24)
    async def cleanup_loop(self):
        db.cleanup_old_players()


async def setup(bot):
    await bot.add_cog(PlayerProgress(bot))
