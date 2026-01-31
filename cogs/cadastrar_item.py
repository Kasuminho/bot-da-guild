import os
import time
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

import db
from config import STAFF_ROLE_ID

ASSETS_DIR = "assets/forum_items"
os.makedirs(ASSETS_DIR, exist_ok=True)


class ItemRegister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cadastraritem", description="Cadastrar um novo item")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.describe(
        kind="Tipo do item (Equipamento ou Skill)",
        category="Categoria do item",
        item_pt="Nome do item em português",
        item_en="Nome do item em inglês",
        type_pt="Tipo em português",
        type_en="Tipo em inglês",
        image1="Primeira imagem",
        image2="Segunda imagem",
    )
    async def cadastraritem(
        self,
        interaction: discord.Interaction,
        kind: Literal["equipment", "skill"],
        category: Literal["rare", "heroic", "legendary"],
        item_pt: str,
        item_en: str,
        type_pt: str,
        type_en: str,
        image1: discord.Attachment,
        image2: discord.Attachment,
    ):
        await interaction.response.defer(ephemeral=True)

        # salva imagens
        timestamp = int(time.time())
        item_dir = os.path.join(ASSETS_DIR, str(timestamp))
        os.makedirs(item_dir, exist_ok=True)
        path1 = os.path.join(item_dir, "1.png")
        path2 = os.path.join(item_dir, "2.png")
        await image1.save(path1)
        await image2.save(path2)

        # cadastra no DB
        db.add_forum_item(
            kind=kind,  # tipo será escolhido no /anunciar
            category=category,
            item_pt=item_pt,
            item_en=item_en,
            type_pt=type_pt,
            type_en=type_en,
            image1_path=path1,
            image2_path=path2,
        )

        await interaction.followup.send(
            f"✅ Item `{item_pt} / {item_en}` cadastrado com sucesso!", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ItemRegister(bot))
