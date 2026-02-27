import time
import asyncio
from io import BytesIO
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import aiohttp
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
    EXTRAORDINARY_STAFF_CHANNEL_ID,
    EXTRAORDINARY_STAFF_WEBHOOK_URL,
    FORUM_ANNOUNCE_TEST_MODE,
)
from utils.image_storage import is_remote_url

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
        await self.flow.finalize(ts, interaction)


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

    def _extract_google_drive_file_id(self, url: str):
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if "drive.google.com" not in host:
            return None

        if "/file/d/" in parsed.path:
            return parsed.path.split("/file/d/", 1)[1].split("/", 1)[0]

        query = parse_qs(parsed.query)
        return (query.get("id") or [None])[0]

    def _candidate_download_urls(self, url: str):
        file_id = self._extract_google_drive_file_id(url)
        if not file_id:
            return [url]

        return [
            f"https://drive.google.com/uc?export=download&id={file_id}",
            f"https://drive.google.com/thumbnail?id={file_id}&sz=w2000",
            url,
        ]

    def _looks_like_image(self, content: bytes) -> bool:
        if content.startswith((
            b"\x89PNG\r\n\x1a\n",
            b"\xff\xd8\xff",
            b"GIF87a",
            b"GIF89a",
            b"BM",
        )):
            return True

        return content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP"

    async def _download_remote_image_as_file(self, session: aiohttp.ClientSession, url: str, fallback_name: str):
        for candidate_url in self._candidate_download_urls(url):
            try:
                async with session.get(candidate_url, timeout=20) as response:
                    if response.status != 200:
                        continue

                    content_type = (response.headers.get("Content-Type") or "").lower()
                    content = await response.read()
                    if not content:
                        continue

                    if not content_type.startswith("image/"):
                        if not self._looks_like_image(content):
                            continue

                    return discord.File(BytesIO(content), filename=fallback_name)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

        return None

    async def _build_thread_files(self, item):
        async with aiohttp.ClientSession() as session:
            files = []
            failed_urls = []

            for index, url in enumerate((item[7], item[8]), start=1):
                if not is_remote_url(url):
                    files.append(discord.File(url))
                    continue

                file = await self._download_remote_image_as_file(session, url, f"forum_items_{item[0]}_{index}.png")
                if file:
                    files.append(file)
                else:
                    failed_urls.append(url)

            return files, failed_urls

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

    async def finalize(self, timestamp, interaction):
        forum = self.guild.get_channel(FORUM_CHANNEL_ID)
        for item_id in self.item_ids:
            item = db.get_forum_item(item_id)

            initial_content = f"<t:{timestamp}:F>"
            create_thread_kwargs = {
                "name": f"📢 Anúncio – {item[3]} / {item[4]}",
                "content": initial_content,
                "applied_tags": [discord.Object(id=FORUM_TAG_ID)],
            }

            files, failed_remote_urls = await self._build_thread_files(item)
            if files:
                create_thread_kwargs["files"] = files

            if failed_remote_urls:
                create_thread_kwargs["content"] = (
                    f"{initial_content}\n"
                    + "\n".join(f"📎 {url}" for url in failed_remote_urls)
                )

            post = await forum.create_thread(**create_thread_kwargs)

            criteria = CRITERIA_TEXTS[(item[1], self.mode)]
            warning_prefix = ""
            if FORUM_ANNOUNCE_TEST_MODE:
                warning_prefix = (
                    "🚨🚨🚨 **ATENÇÃO: POST DE TESTE DO BOT** 🚨🚨🚨\n"
                    "⚠️ **NÃO É ANÚNCIO REAL. ESTE POST É EXCLUSIVO PARA TESTAR IMPLEMENTAÇÕES.** ⚠️\n"
                    "❌ **IGNORE ESTE TÓPICO PARA DECISÕES DE JOGO.** ❌\n\n"
                )

            await post.thread.send(
                f"{warning_prefix}"
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
    PARTICIPANT_REACTIONS = [
        "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
        "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
        "🇺", "🇻", "🇼", "🇽", "🇾", "🇿",
    ]

    def _is_heroic_item(self, item_name: str) -> bool:
        candidates = [item_name.strip()]

        if " / " in item_name:
            left, right = item_name.split(" / ", 1)
            candidates.extend([left.strip(), right.strip()])

        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = candidate.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)

            category = db.get_forum_item_category_by_name(candidate)
            if (category or "").casefold() == "heroic":
                return True

        return False

    def _extract_item_name_from_thread(self, thread_name: str) -> str:
        if "–" in thread_name:
            return thread_name.split("–", 1)[1].strip()
        if "-" in thread_name:
            return thread_name.split("-", 1)[1].strip()
        return thread_name

    def _extract_image_url(self, message: discord.Message):
        if message.attachments:
            return message.attachments[0].url

        for emb in message.embeds:
            if emb.image and emb.image.url:
                return emb.image.url
            if emb.thumbnail and emb.thumbnail.url:
                return emb.thumbnail.url

        return None

    async def _collect_participants(self, thread: discord.Thread):
        participants = []
        seen = set()
        first_media_message = None

        async for message in thread.history(limit=500, oldest_first=True):
            if message.author.bot:
                continue

            if message.author.id not in seen:
                seen.add(message.author.id)
                participants.append(message.author)

            if not first_media_message and self._extract_image_url(message):
                first_media_message = message

        return participants, first_media_message

    async def _send_to_extraordinary_staff(self, embed: discord.Embed):
        if EXTRAORDINARY_STAFF_WEBHOOK_URL:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(
                    EXTRAORDINARY_STAFF_WEBHOOK_URL,
                    session=session,
                )
                await webhook.send(embed=embed, username="Guild Staff Assistant")
            return

        if EXTRAORDINARY_STAFF_CHANNEL_ID <= 0:
            return

        extra_channel = self.bot.get_channel(EXTRAORDINARY_STAFF_CHANNEL_ID)
        if not extra_channel:
            extra_channel = await self.bot.fetch_channel(EXTRAORDINARY_STAFF_CHANNEL_ID)

        review_message = await extra_channel.send(embed=embed)
        return review_message

    async def _send_extraordinary_staff_review(self, thread: discord.Thread):
        if EXTRAORDINARY_STAFF_CHANNEL_ID <= 0 and not EXTRAORDINARY_STAFF_WEBHOOK_URL:
            return

        item_name = self._extract_item_name_from_thread(thread.name)
        if not self._is_heroic_item(item_name):
            return

        participants, media_message = await self._collect_participants(thread)
        if not participants:
            return

        limited_participants = participants[: len(self.PARTICIPANT_REACTIONS)]
        lines = []
        for idx, member in enumerate(limited_participants):
            lines.append(f"{self.PARTICIPANT_REACTIONS[idx]} {member.display_name} (`{member.id}`)")

        if len(participants) > len(limited_participants):
            lines.append(
                f"... e mais {len(participants) - len(limited_participants)} participante(s)"
            )

        embed = discord.Embed(
            title="🟣 Votação extraordinária de drop heroico",
            description=(
                "Anúncio heroico encerrado automaticamente.\n"
                "Reajam no emoji do participante que deve receber este item."
            ),
            color=discord.Color.purple(),
        )
        embed.add_field(name="🧩 Item", value=item_name, inline=False)
        embed.add_field(name="🧵 Thread", value=thread.mention, inline=False)
        embed.add_field(name="🔗 Link", value=thread.jump_url, inline=False)
        embed.add_field(
            name=f"👥 Participantes ({len(participants)})",
            value="\n".join(lines),
            inline=False,
        )
        embed.set_footer(text="Use apenas 1 reação por staff para evitar conflito na decisão.")

        if media_message:
            image_url = self._extract_image_url(media_message)
            if image_url:
                embed.set_image(url=image_url)

        review_message = await self._send_to_extraordinary_staff(embed)
        if not review_message:
            return

        for idx in range(len(limited_participants)):
            await review_message.add_reaction(self.PARTICIPANT_REACTIONS[idx])

    def __init__(self, bot):
        self.bot = bot
        self.check_forum_posts.start()
        
    @tasks.loop(minutes=1)
    async def check_forum_posts(self):
        now = int(time.time())
        expired = db.get_open_forum_posts(now)

        for post_id, thread_id in expired:
            thread = self.bot.get_channel(thread_id)
            if not thread:
                try:
                    thread = await self.bot.fetch_channel(thread_id)
                except Exception:
                    thread = None

            if thread:
                await thread.send("⏰ **Anúncio encerrado automaticamente.**")
                try:
                    await self._send_extraordinary_staff_review(thread)
                except Exception:
                    pass
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
