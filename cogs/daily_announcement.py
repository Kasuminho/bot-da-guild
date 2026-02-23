import datetime
import os
import tempfile
import time

import discord
from deep_translator import GoogleTranslator
from discord import app_commands
from discord.ext import commands, tasks

import db
from utils.image_storage import is_remote_storage_enabled, is_remote_url, upload_image

FORCE_CHANNEL_ID = 1431340166877806644
IMAGE_DIR = "images/daily"


class AnnouncementSelect(discord.ui.Select):
    def __init__(self, announcements):
        options = [
            discord.SelectOption(label=ann[1][:80], value=str(ann[0]))
            for ann in announcements
        ]

        super().__init__(
            placeholder="Selecione o aviso para desativar", options=options
        )

    async def callback(self, interaction: discord.Interaction):
        ann_id = int(self.values[0])
        db.deactivate_daily_announcement(ann_id)
        await interaction.response.send_message(
            "✅ Aviso desativado com sucesso.", ephemeral=True
        )


class AnnouncementView(discord.ui.View):
    def __init__(self, announcements):
        super().__init__(timeout=60)
        self.add_item(AnnouncementSelect(announcements))


class DailyAnnouncement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs(IMAGE_DIR, exist_ok=True)
        self.hourly_loop.start()

    # =========================
    # CREATE ANNOUNCEMENT
    # =========================
    @app_commands.command(
        name="aviso_diario", description="Cria um aviso diário (máx 4 ativos)"
    )
    async def aviso_diario(
        self,
        interaction: discord.Interaction,
        texto_pt: str,
        imagem_pt: discord.Attachment,
        imagem_en: discord.Attachment,
    ):
        await interaction.response.defer(ephemeral=True)

        active = db.get_active_daily_announcements()
        if len(active) >= 4:
            await interaction.followup.send(
                "❌ Limite de 4 avisos ativos atingido.", ephemeral=True
            )
            return

        if not imagem_pt.content_type.startswith(
            "image"
        ) or not imagem_en.content_type.startswith("image"):
            await interaction.followup.send(
                "❌ Os anexos precisam ser imagens.", ephemeral=True
            )
            return

        texto_en = GoogleTranslator(source="pt", target="en").translate(texto_pt)

        ts = int(time.time())

        if is_remote_storage_enabled():
            with tempfile.TemporaryDirectory(prefix="daily_announcement_") as temp_dir:
                local_pt = os.path.join(temp_dir, "pt.png")
                local_en = os.path.join(temp_dir, "en.png")
                await imagem_pt.save(local_pt)
                await imagem_en.save(local_en)

                img_pt_path = upload_image(local_pt, f"daily_{ts}_pt.png")
                img_en_path = upload_image(local_en, f"daily_{ts}_en.png")
        else:
            img_pt_path = f"{IMAGE_DIR}/{ts}_pt.png"
            img_en_path = f"{IMAGE_DIR}/{ts}_en.png"
            await imagem_pt.save(img_pt_path)
            await imagem_en.save(img_en_path)

        db.add_daily_announcement(texto_pt, texto_en, img_pt_path, img_en_path)

        await interaction.followup.send(
            "✅ Aviso diário criado com sucesso.", ephemeral=True
        )

    # =========================
    # DISABLE ANNOUNCEMENT
    # =========================
    @app_commands.command(
        name="aviso_diario_desativar", description="Desativa um aviso diário específico"
    )
    async def aviso_diario_desativar(self, interaction: discord.Interaction):
        anns = db.get_active_daily_announcements()

        if not anns:
            await interaction.response.send_message(
                "❌ Nenhum aviso ativo.", ephemeral=True
            )
            return

        view = AnnouncementView(anns)
        await interaction.response.send_message(
            "Selecione o aviso que deseja desativar:", view=view, ephemeral=True
        )

    # =========================
    # HOURLY LOOP
    # =========================
    @tasks.loop(minutes=1)
    async def hourly_loop(self):
        now = datetime.datetime.now()

        if now.minute != 0:
            return

        if not (12 <= now.hour <= 15):
            return

        index = now.hour - 12
        anns = db.get_active_daily_announcements()

        if index >= len(anns):
            return

        await self.send_single_announcement(anns[index])

    async def send_single_announcement(self, ann):
        channel = self.bot.get_channel(FORCE_CHANNEL_ID)
        if not channel:
            return

        perms = channel.permissions_for(channel.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.attach_files):
            return

        _, text_pt, text_en, img_pt, img_en = ann

        files = []

        embed_pt = discord.Embed(title="📢 Aviso", description=text_pt, color=0x2ECC71)
        embed_en = discord.Embed(title="📢 Notice", description=text_en, color=0x3498DB)

        if is_remote_url(img_pt) and is_remote_url(img_en):
            embed_pt.set_image(url=img_pt)
            embed_en.set_image(url=img_en)
        else:
            files = [
                discord.File(img_pt, filename="pt.png"),
                discord.File(img_en, filename="en.png"),
            ]
            embed_pt.set_image(url="attachment://pt.png")
            embed_en.set_image(url="attachment://en.png")

        await channel.send(embeds=[embed_pt, embed_en], files=files)


async def setup(bot):
    await bot.add_cog(DailyAnnouncement(bot))
