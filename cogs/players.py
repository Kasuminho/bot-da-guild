from datetime import datetime, timedelta, timezone
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

import db
from config import CATEGORY_ID, STAFF_ROLE_ID

PlayerClass = Literal[
    "🏥 Divine Caster",
    "☠️ Deathbringer",
    "🧙‍♂️ Elementalist",
    "🔫 Gunslinger",
    "🏹 Night Ranger",
    "🏹 Destroyer",
    "🛡️ Vanguard",
    "⚔️ Berserker",
    "🗡️ Assassin",
]

PlayerIcon = {
    "🏥 Divine Caster": "🏥",
    "☠️ Deathbringer": "☠️",
    "🧙‍♂️ Elementalist": "🧙‍♂️",
    "🔫 Gunslinger": "🔫",
    "🏹 Night Ranger": "🏹",
    "🏹 Destroyer": "🏹",
    "🛡️ Vanguard": "🛡️",
    "⚔️ Berserker": "⚔️",
    "🗡️ Assassin": "🗡️",
}

class Players(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------------
    # CADASTRAR JOGADOR
    # -------------------------
    @app_commands.command(name="cadastrarjogador")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def cadastrar_jogador(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member,
        nick_ingame: str,
        idioma: Literal["PT", "EN"],
        classe: PlayerClass,  # 👈 NOVO
    ):
        guild = interaction.guild
        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            staff_role: discord.PermissionOverwrite(view_channel=True),
            jogador: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
        }

        channel = await guild.create_text_channel(
            name= f"{PlayerIcon[classe]}{nick_ingame.lower()}",
            category=guild.get_channel(CATEGORY_ID),
            overwrites=overwrites,
        )

        try:
            await jogador.edit(nick=nick_ingame)
        except discord.Forbidden:
            pass

        # 👇 SALVA CLASSE JUNTO
        db.add_player(
            jogador.id,
            nick_ingame,
            idioma,
            channel.id,
        )

        msg = (
            f"Oi, {jogador.mention}! Bem-vindo ao G3X! 🔥\n\n"
            f"Como você entrou recentemente, queria explicar um procedimento que já utilizamos "
            f"com todos os membros para ajudar no progresso dentro da guilda.\n\n"
            f"Coletamos algumas capturas de tela da sua conta para que possamos revisar seu progresso "
            f"e fornecer dicas personalizadas de melhoria. Isso nos ajuda a entender seus pontos fortes "
            f"e ver onde podemos apoiar ainda mais seu crescimento.\n\n"
            f"Quando possível, por favor, envie capturas de tela de:\n\n"
            f"• Stellas – Amplificação\n"
            f"• Equipamentos\n"
            f"• Relíquias\n"
            f"• Estigma\n"
            f"• Coleção de itens\n"
            f"• Habilidades\n"
            f"• Pedras do Paraíso\n\n"
            f"Isso é algo que já fazemos com todos desde o início, e como você não viu o primeiro anúncio, "
            f"estamos apenas compartilhando com você agora. 😊\n\n"
            f"Se você tiver alguma dúvida sobre como tirar ou enviar as capturas de tela, "
            f"fique à vontade para entrar em contato com qualquer ADM. Estamos aqui para ajudar!\n\n"
            f"🧩 **Classe:** {classe}"
            if idioma == "PT"
            else
            f"Hi, {jogador.mention}! Welcome to G3X! 🔥\n\n"
            f"Since you joined recently, I wanted to explain a procedure we already use "
            f"with all members to help with progression inside the guild.\n\n"
            f"We collect some screenshots of your account so we can review your progression "
            f"and provide personalized improvement tips. This helps us understand your strengths "
            f"and see where we can support your growth even further.\n\n"
            f"When possible, please send screenshots of:\n\n"
            f"• Stellas – Amplification\n"
            f"• Equipment\n"
            f"• Relics\n"
            f"• Stigma\n"
            f"• Item Collection\n"
            f"• Skills\n"
            f"• Heavenstones\n\n"
            f"This is something we’ve done with everyone from the start, and since you didn’t see "
            f"the first announcement, we’re just sharing it with you now. 😊\n\n"
            f"If you have any questions about how to take or send the screenshots, "
            f"feel free to contact any ADM. We’re here to help!\n\n"
            f"🧩 **Class:** {classe}"
        )


        await channel.send(msg)
        await interaction.response.send_message(
            "Jogador cadastrado com sucesso.", ephemeral=True
        )

    # -------------------------
    # ASSOCIAR CANAL
    # -------------------------
    @app_commands.command(name="associarcanal")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def associar_canal(
        self,
        interaction: discord.Interaction,
        jogador: discord.Member,
        canal: discord.TextChannel,
        idioma: Literal["PT", "EN"],
    ):

        db.upsert_player_channel_with_language(jogador.id, idioma, canal.id)

        await interaction.response.send_message(
            "Canal associado e idioma registrado com sucesso.", ephemeral=True
        )

    # -------------------------
    # VERIFICAR INATIVOS (PUTO)
    # -------------------------
    @app_commands.command(name="verificarinativos")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def verificar_inativos(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        limite = datetime.now(timezone.utc) - timedelta(days=3)
        players = db.get_all_players()
        # esperado: (discord_id, channel_id, idioma)

        total_alertas = 0

        for _, discord_id, _, idioma, channel_id, _ in players:
            guild = interaction.guild
            channel = guild.get_channel(channel_id)
            member = guild.get_member(discord_id)

            if not channel or not member:
                continue

            ultima_msg = None

            async for msg in channel.history(limit=50):
                if msg.author.id == discord_id:
                    ultima_msg = msg.created_at
                    break

            if not ultima_msg or ultima_msg < limite:
                total_alertas += 1

                if idioma == "PT":
                    texto = (
                        f"{member.mention}\n\n"
                        f"⚠️ **CADE A ATUALIZAÇÃO, MEU CONSAGRADO?**\n\n"
                        f"Já fazem **mais de 3 dias** que você não posta nada aqui.\n"
                        f"Esse canal existe **JUSTAMENTE** pra isso.\n\n"
                        f"Posta tua atualização o quanto antes pra não virar problema.\n"
                        f"Obrigado."
                    )
                else:
                    texto = (
                        f"{member.mention}\n\n"
                        f"⚠️ **WHERE IS YOUR UPDATE?**\n\n"
                        f"It has been **over 3 days** without any update from you.\n"
                        f"This channel exists **exactly** for that purpose.\n\n"
                        f"Please post your update as soon as possible.\n"
                        f"Thank you."
                    )

                await channel.send(texto)

        await interaction.followup.send(
            f"Verificação concluída. Alertas enviados: **{total_alertas}**.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Players(bot))
