import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, Select, TextInput, View, Button

import db
from config import (
    FORUM_CHANNEL_ID,
    FORUM_TAG_ID,
    G3X_ROLE_ID,
    STAFF_CHANNEL_ID,
    STAFF_ROLE_ID,
)

# ==========================================================
# CONSTANTES
# ==========================================================
ITEMS_PER_PAGE = 25
WINDOW_DAYS = 7
MIN_PERCENT = 90
MAX_T4_ABSENCES = 1

TIMEZONES = {
    "Brasil (America/Sao_Paulo)": "America/Sao_Paulo",
    "UTC": "UTC",
}

CRITERIA_TEXTS = { 
                  ("skill", "PvE"): { 
                      "pt": ( 
                          "• Jogadores que utilizam esta skill\n" 
                          "• Skill inferior à anunciada\n" 
                          "• Participação em boss é obrigatória" 
                          ), 
                      "en": ( 
                          "• Players who use this skill\n" 
                          "• Skill inferior to the announced one\n" 
                          "• Boss participation is mandatory" 
                          ), 
                      }, 
                  ("skill", "PvP"): { 
                      "pt": ( 
                          "• Jogadores que utilizam esta skill\n" 
                          "• Skill inferior à anunciada\n" 
                          "• Level 75+ obrigatório\n" 
                          "• Prioridade por nível\n" 
                          ), 
                      "en": ( 
                          "• Players who use this skill\n" 
                          "• Skill inferior to the announced one\n" 
                          "• Mandatory Level 75+\n" "• Priority by level\n" 
                          ), 
                      }, 
                  ("equipment", "PvE"): { 
                      "pt": ( 
                          "• Jogadores que utilizam este equipamento\n" 
                          "• Equipamento inferior ao anunciado\n" 
                          "• Participação em boss é obrigatória" ), 
                      "en": ( 
                          "• Players who use this equipment\n" 
                          "• Equipment inferior to the announced one\n" 
                          "• Boss participation is mandatory" ), 
                      }, 
                  ("equipment", "PvP"): { 
                      "pt": ( 
                          "• Jogadores que utilizam este equipamento\n" 
                          "• Equipamento inferior ao anunciado\n" 
                          "• Level 75+ obrigatório\n" 
                          "• Prioridade para quem falta ao item\n" 
                          "• Enviar print dos equipamentos PvP" 
                          ), 
                      "en": ( 
                          "• Players who use this equipment\n" 
                          "• Equipment inferior to the announced one\n" 
                          "• Mandatory Level 75+\n" 
                          "• Priority for players missing the item\n" 
                          "• Send PvP equipment screenshot" ), 
                      }, 
                  }

# ==========================================================
# ELEGIBILIDADE
# ==========================================================
def evaluate_eligibility(discord_id: int):
    until = datetime.utcnow()
    since = until - timedelta(days=WINDOW_DAYS)

    stats = db.get_participation_stats(
        discord_id,
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
        reasons.append(f"Participação abaixo de {MIN_PERCENT}% ({percent}%)")

    if t4_absences > MAX_T4_ABSENCES:
        eligible = False
        reasons.append("2 ou mais faltas em rotações T4")

    return eligible, percent, t4_absences, reasons


# ==========================================================
# MODAL DATA / HORA
# ==========================================================
class DateTimeModal(Modal, title="Finalizar anúncio"):
    datetime_input = TextInput(
        label="Data e hora",
        placeholder="YYYY-MM-DD HH:MM",
        required=True,
    )

    def __init__(self, flow, tz_name):
        super().__init__()
        self.flow = flow
        self.tz_name = tz_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tz = ZoneInfo(self.tz_name)
            local_dt = datetime.strptime(
                self.datetime_input.value, "%Y-%m-%d %H:%M"
            ).replace(tzinfo=tz)

            utc_dt = local_dt.astimezone(timezone.utc)
            ts = int(utc_dt.timestamp())
        except ValueError:
            await interaction.response.send_message(
                "❌ Formato inválido. Use YYYY-MM-DD HH:MM",
                ephemeral=True,
            )
            return

        if ts <= int(time.time()):
            await interaction.response.send_message(
                "❌ A data precisa ser no futuro.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.flow.finalize(ts, interaction, self.tz_name)


# ==========================================================
# TIMEZONE
# ==========================================================
class TimezoneSelect(Select):
    def __init__(self, flow):
        options = [
            discord.SelectOption(label=k, value=v)
            for k, v in TIMEZONES.items()
        ]
        super().__init__(placeholder="Selecione o fuso horário", options=options)
        self.flow = flow

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DateTimeModal(self.flow, self.values[0])
        )


class TimezoneView(View):
    def __init__(self, flow):
        super().__init__(timeout=60)
        self.add_item(TimezoneSelect(flow))


# ==========================================================
# SELECT TIPO
# ==========================================================
class ItemTypeSelect(Select):
    def __init__(self, flow):
        super().__init__(
            placeholder="Tipo do item",
            options=[
                discord.SelectOption(label="Skill", value="skill"),
                discord.SelectOption(label="Equipment", value="equipment"),
            ],
        )
        self.flow = flow

    async def callback(self, interaction: discord.Interaction):
        self.flow.item_type = self.values[0]
        self.flow.item_ids = []
        self.flow.last_selected_id = None
        self.flow.page = 0
        await self.flow.show_item_page(interaction)


# ==========================================================
# SELECT PAGINADO
# ==========================================================
class ItemPageSelect(Select):
    def __init__(self, flow, items, last_selected_id):
        options = [
            discord.SelectOption(
                label=f"{pt} / {en}",
                value=str(item_id),
                default=item_id == last_selected_id,
            )
            for item_id, pt, en in items
        ]
        super().__init__(
            placeholder="Selecione um item (um por vez)",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.flow = flow
        self.page_items = items

    async def callback(self, interaction: discord.Interaction):
        selected_id = int(self.values[0])
        if selected_id not in self.flow.item_ids:
            self.flow.item_ids.append(selected_id)
        self.flow.last_selected_id = selected_id
        await self.flow.show_item_page(interaction)


class PrevPageButton(Button):
    def __init__(self, flow):
        super().__init__(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
        self.flow = flow

    async def callback(self, interaction: discord.Interaction):
        self.flow.page -= 1
        await self.flow.show_item_page(interaction)


class NextPageButton(Button):
    def __init__(self, flow):
        super().__init__(label="➡️ Próximo", style=discord.ButtonStyle.secondary)
        self.flow = flow

    async def callback(self, interaction: discord.Interaction):
        self.flow.page += 1
        await self.flow.show_item_page(interaction)


class ConfirmItemsButton(Button):
    def __init__(self, flow):
        super().__init__(label="✅ Confirmar itens", style=discord.ButtonStyle.primary)
        self.flow = flow

    async def callback(self, interaction: discord.Interaction):
        if not self.flow.item_ids:
            await interaction.response.send_message(
                "❌ Selecione ao menos um item.",
                ephemeral=True,
            )
            return
        await self.flow.ask_mode(interaction)


# ==========================================================
# FLOW PRINCIPAL
# ==========================================================
class AnnounceFlow(View):
    def __init__(self, bot, interaction):
        super().__init__(timeout=900)
        self.bot = bot
        self.guild = interaction.guild
        self.author_id = interaction.user.id

        self.item_type = None
        self.item_ids = []
        self.last_selected_id = None
        self.page = 0
        self.items = []

        self.add_item(ItemTypeSelect(self))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Esse fluxo não é seu.",
                ephemeral=True,
            )
            return False
        return True

    async def show_item_page(self, interaction):
        self.clear_items()

        raw_items = db.get_forum_items_for_select()
        self.items = [
            (item_id, pt, en)
            for item_id, kind, pt, en in raw_items
            if kind == self.item_type
        ]

        if not self.items:
            await interaction.response.send_message(
                "❌ Nenhum item disponível.",
                ephemeral=True,
            )
            return

        start = self.page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE

        self.add_item(
            ItemPageSelect(self, self.items[start:end], self.last_selected_id)
        )
        self.add_item(ConfirmItemsButton(self))

        if self.page > 0:
            self.add_item(PrevPageButton(self))
        if end < len(self.items):
            self.add_item(NextPageButton(self))

        await interaction.response.edit_message(
            content=self.build_selection_content(),
            view=self,
        )

    def build_selection_content(self):
        header = "📢 **Fluxo de anúncio iniciado**"
        if not self.item_type:
            return header
        if not self.item_ids:
            return f"{header}\n\nNenhum item selecionado."
        item_lookup = {item_id: (pt, en) for item_id, pt, en in self.items}
        selected_items = []
        for item_id in self.item_ids:
            if item_id in item_lookup:
                pt, en = item_lookup[item_id]
                selected_items.append(f"- {pt} / {en}")
        selected_text = "\n".join(selected_items)
        return f"{header}\n\n**Itens selecionados:**\n{selected_text}"

    async def ask_mode(self, interaction):
        self.clear_items()
        select = Select(
            placeholder="Modo do item",
            options=[
                discord.SelectOption(label="PvE", value="PvE"),
                discord.SelectOption(label="PvP", value="PvP"),
            ],
        )
        select.callback = self.on_mode_selected
        self.add_item(select)
        await interaction.response.edit_message(
            content=self.build_selection_content(),
            view=self,
        )

    async def on_mode_selected(self, interaction):
        self.mode = interaction.data["values"][0]
        self.clear_items()
        await interaction.response.send_message(
            "🌍 Selecione o fuso horário:",
            view=TimezoneView(self),
            ephemeral=True,
        )

    async def finalize(self, timestamp, interaction, tz_name):
        forum = self.guild.get_channel(FORUM_CHANNEL_ID)
        for item_id in self.item_ids:
            item = db.get_forum_item(item_id)

            post = await forum.create_thread(
                name=f"📢 Anúncio – {item[3]} / {item[4]}",
                content=f"<t:{timestamp}:F> `{tz_name}`",
                files=[discord.File(item[7]), discord.File(item[8])],
                applied_tags=[discord.Object(id=FORUM_TAG_ID)],
            )

            criteria = CRITERIA_TEXTS[(item[1], self.mode)]
            await post.thread.send(
                f"<@&{G3X_ROLE_ID}>\n\n"
                f"🇧🇷 **Português**\n"
                f"🟣 **Item:** {item[3]}\n"
                f"📌 **Tipo:** {item[5]}\n"
                f"🎯 **Categoria:** {self.mode}\n\n"
                f"{criteria['pt']}\n\n"
                f"🇺🇸 **English**\n"
                f"🟣 **Item:** {item[4]}\n"
                f"📌 **Type:** {item[6]}\n"
                f"🎯 **Category:** {self.mode}\n\n"
                f"{criteria['en']}\n\n"
                f"⏰ <t:{timestamp}:F>"
            )

            db.add_forum_post(post.thread.id, timestamp)

        await interaction.followup.send(
            "✅ Anúncio criado com sucesso.",
            ephemeral=True,
        )


# ==========================================================
# COG
# ==========================================================
class ForumAnnounce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_forum_posts.start()
        
    @tasks.loop(minutes=1)
    async def check_forum_posts(self):
        now = int(time.time())
        expired = db.get_open_forum_posts(now)

        for post_id, thread_id in expired:
            thread = self.bot.get_channel(thread_id)
            if thread:
                await thread.send("⏰ **Anúncio encerrado automaticamente.**")
                await thread.edit(locked=True)
            db.mark_forum_post_closed(post_id)

    @check_forum_posts.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="anunciar", description="Anúncio guiado")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def anunciar(self, interaction: discord.Interaction):
        if interaction.channel_id != STAFF_CHANNEL_ID:
            await interaction.response.send_message(
                "Somente no canal da staff.",
                ephemeral=True,
            )
            return

        view = AnnounceFlow(self.bot, interaction)
        await interaction.response.send_message(
            "📢 **Fluxo de anúncio iniciado**",
            view=view,
        )


async def setup(bot):
    await bot.add_cog(ForumAnnounce(bot))
