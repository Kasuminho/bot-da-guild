import time

import discord
from discord import app_commands
from discord.ext import commands

import db
from config import FORUM_CHANNEL_ID, STAFF_ROLE_ID, DELIVERY_LOG_CHANNEL_ID

OVERRIDE_IDS = {273600843251712020, 314170587968700417}
STAFF_CONTACT_ID = 273600843251712020


class ForumDelivery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ======================================================
    # UTIL — COLETAR PRINTS ANTERIORES
    # ======================================================
    async def _collect_attachments(
        self,
        thread: discord.Thread,
        user_id: int,
        limit: int = 60,
    ):
        attachments = []

        async for msg in thread.history(limit=limit, oldest_first=False):
            # Para se não for o mesmo staff
            if msg.author.id != user_id:
                continue

            # Para se a mensagem não tiver anexo
            if not msg.attachments:
                continue

            attachments.extend(msg.attachments)

        return attachments

    # ======================================================
    # ENTREGA
    # ======================================================
    @app_commands.command(name="entregar")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def entregar(
        self,
        interaction: discord.Interaction,
        jogadores: str,  # menções: @A @B @C
        item: str,
    ):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        # Precisa ser thread
        if not isinstance(channel, discord.Thread):
            await interaction.followup.send(
                "❌ Use este comando dentro de uma thread.",
                ephemeral=True,
            )
            return

        # Precisa ser thread do fórum correto
        if channel.parent_id != FORUM_CHANNEL_ID:
            await interaction.followup.send(
                "❌ Este comando só pode ser usado em threads do fórum correto.",
                ephemeral=True,
            )
            return

        post = db.get_forum_post_by_thread(channel.id)

        if not post:
            await interaction.followup.send(
                "❌ Thread não registrada.",
                ephemeral=True,
            )
            return

        post_id, close_time, closed, delivered = post
        now = int(time.time())

        if delivered:
            await interaction.followup.send(
                "⚠️ Já finalizado.",
                ephemeral=True,
            )
            return

        if now < close_time and interaction.user.id not in OVERRIDE_IDS:
            await interaction.followup.send(
                f"⏰ Ainda aberto. Fecha em <t:{close_time}:F>",
                ephemeral=True,
            )
            return

        override = now < close_time and interaction.user.id in OVERRIDE_IDS

        if override:
            await channel.send(
                "⚠️ **Entrega realizada antes do horário por override administrativo.**"
            )

        # =============================
        # PROCESSA JOGADORES
        # =============================
        player_ids = [
            int(word[2:-1])
            for word in jogadores.split()
            if word.startswith("<@") and word.endswith(">")
        ]

        players: list[discord.Member] = []

        for pid in player_ids:
            member = interaction.guild.get_member(pid)
            if member:
                players.append(member)

        if not players:
            await interaction.followup.send(
                "❌ Nenhum jogador válido encontrado nas menções.",
                ephemeral=True,
            )
            return

        # =============================
        # COLETA PRINTS ANTERIORES
        # =============================
        attachments = await self._collect_attachments(
            channel,
            interaction.user.id,
        )

        if not attachments:
            await interaction.followup.send(
                "❌ Envie os prints **antes** de usar o comando `/entregar`.",
                ephemeral=True,
            )
            return

        # =============================
        # CANAL DE LOG / ENTREGA
        # =============================
        delivery_channel = interaction.guild.get_channel(DELIVERY_LOG_CHANNEL_ID)
        if delivery_channel is None:
            # fallback: tenta buscar da API
            try:
                delivery_channel = await interaction.guild.fetch_channel(DELIVERY_LOG_CHANNEL_ID)
            except discord.NotFound:
                delivery_channel = None

        if delivery_channel is None:
            await interaction.followup.send(
                "❌ Canal de entrega/log não encontrado. Verifique o DELIVERY_LOG_CHANNEL_ID.",
                ephemeral=True,
            )
            return

        # (opcional) pega link da thread pra referência
        thread_link = f"https://discord.com/channels/{interaction.guild.id}/{channel.id}"

        # monta anexos
        files = [await a.to_file() for a in attachments]
        mentions = " ".join(p.mention for p in players)

        # manda no canal novo
        await delivery_channel.send(
            content=(
                "📦 **Entrega de Item / Item Delivery**\n\n"
                f"🧵 **Thread:** {channel.mention}\n"
                f"🔗 **Link:** {thread_link}\n"
                f"🎯 **Jogadores / Players:** {mentions}\n"
                f"🧾 **Item:** {item}\n"
                f"👤 **Staff:** {interaction.user.mention}\n"
                f"📎 **Comprovantes:** {len(files)} arquivo(s)"
            ),
            files=files,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

        # (opcional) deixa recibo na thread também, sem prints
        await channel.send(
            content=(
                "✅ **Entrega registrada.**\n"
                f"📌 Log enviado em <#{DELIVERY_LOG_CHANNEL_ID}>.\n"
                f"🎯 Players: {mentions}\n"
                f"🧾 Item: {item}"
            ),
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )


        # =============================
        # REGISTRO NO BANCO
        # =============================
        for player in players:
            db.add_drop(
                player.id,
                player.display_name,
                item,
                channel.id,
                interaction.user.id,
            )

        db.mark_forum_post_delivered(post_id)

        await channel.edit(archived=True, locked=True)

        await interaction.followup.send(
            f"✅ Entrega registrada para {len(players)} jogador(es).",
            ephemeral=True,
        )

    # ======================================================
    # RECUSAR
    # ======================================================
    @app_commands.command(name="recusar")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def recusar(
        self,
        interaction: discord.Interaction,
        motivo: str,
    ):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        if not isinstance(channel, discord.Thread):
            await interaction.followup.send(
                "❌ Use este comando dentro de uma thread.",
                ephemeral=True,
            )
            return

        if channel.parent_id != FORUM_CHANNEL_ID:
            await interaction.followup.send(
                "❌ Este comando só pode ser usado em requests do fórum correto.",
                ephemeral=True,
            )
            return

        await channel.send(
            content=(
                "❌ **Solicitação recusada pela Staff**\n\n"
                f"Motivo:\n> **{motivo}**\n\n"
                f"📩 Para esclarecimentos, entre em contato com <@{STAFF_CONTACT_ID}>."
            )
        )

        await channel.edit(archived=True, locked=True)

        await interaction.followup.send(
            "✅ Solicitação recusada e thread encerrada.",
            ephemeral=True,
        )

    # ======================================================
    # HISTÓRICO
    # ======================================================
    @app_commands.command(name="historico")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def historico(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member,
    ):
        drops = db.get_player_drops(jogador.id)

        if not drops:
            await interaction.response.send_message(
                f"📦 {jogador.mention} ainda não recebeu nenhum item.",
                ephemeral=True,
            )
            return

        linhas = []

        for item, delivered_at, delivered_by in drops:
            staff = interaction.guild.get_member(delivered_by)
            staff_name = staff.mention if staff else f"`{delivered_by}`"

            linhas.append(
                f"• **{item}**\n"
                f"  ⏰ <t:{delivered_at}:R>\n"
                f"  👤 Entregue por: {staff_name}"
            )

        texto = (
            f"📜 **Histórico de Drops — {jogador.display_name}**\n\n"
            + "\n\n".join(linhas)
        )

        await interaction.response.send_message(texto, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ForumDelivery(bot))
