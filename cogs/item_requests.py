import time
import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID
import db
from utils.i18n import TEXT
from utils.fixed_items import (
    CATEGORY_LABELS,
    FIXED_ITEMS,
    ITEM_CATEGORIES,
    ITEM_CHOICES,
)

lang = "pt"

EXEMPT_FROM_CATEGORY_LIMIT = {
    "creature of gaiety",
    "elder dragon isteria",
}


class ItemRequests(commands.Cog):
    """
    Gerencia requests de itens baseados em THREAD DE FÓRUM.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================================
    # HELPERS
    # ==========================================================

    def ensure_thread(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.Thread):
            raise app_commands.AppCommandError(TEXT["thread_only"][lang])

    def get_player_language(self, discord_id: int) -> str:
        player_language = db.get_player_language(discord_id)
        if not player_language:
            return "pt"
        normalized = player_language.strip().lower()
        if normalized == "en":
            return "en"
        return "pt"

    async def active_thread_item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if not isinstance(interaction.channel, discord.Thread):
            return []

        items = db.get_active_request_items_by_thread(interaction.channel.id)
        if current:
            current_lower = current.lower()
            items = [item for item in items if current_lower in item.lower()]

        return [
            app_commands.Choice(
                name=f"{FIXED_ITEMS[item]['pt']} / {FIXED_ITEMS[item]['en']}",
                value=item,
            )
            for item in items[:25]
            if item in FIXED_ITEMS
        ]

    def normalize_last_update(self, request_id: int, last_update: int) -> int:
        """
        Corrige timestamps inválidos:
        - ms → s
        - timestamp no futuro
        """
        now = int(time.time())
        fixed = False

        # veio em milissegundos
        if last_update > 10_000_000_000:
            last_update = int(last_update / 1000)
            fixed = True

        # veio do futuro
        if last_update > now:
            last_update = now
            fixed = True

        if fixed:
            db.fix_last_update(request_id, last_update)

        return last_update

    # ==========================================================
    # CRIAR REQUEST
    # ==========================================================

    @app_commands.command(
        name="request_add",
        description="Cria ou atualiza um request de item (usar dentro da thread)"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.describe(
        player="Player que está solicitando o item",
        item="Item solicitado",
        quantity="Quantidade total desejada"
    )
    @app_commands.choices(item=ITEM_CHOICES)
    async def request_add(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        item: app_commands.Choice[str],
        quantity: int,
    ):
        self.ensure_thread(interaction)
        lang = self.get_player_language(player.id)

        if quantity <= 0:
            await interaction.response.send_message(
                TEXT["qty_invalid"][lang],
                ephemeral=True
            )
            return

        item_key = item.value
        is_exempt = item_key in EXEMPT_FROM_CATEGORY_LIMIT

        item_category = ITEM_CATEGORIES.get(item_key)  # get pra não explodir se faltar
        existing_requests = db.get_item_requests_by_player(player.id)
        has_same_item = item_key in existing_requests

        if not has_same_item and not is_exempt:
            same_category = [
                existing_item
                for existing_item in existing_requests
                # ignora boss existentes na comparação
                if existing_item not in EXEMPT_FROM_CATEGORY_LIMIT
                and ITEM_CATEGORIES.get(existing_item) == item_category
            ]

            if same_category:
                items_list = ", ".join(
                    f"**{FIXED_ITEMS[it][lang]}**" for it in same_category
                )
                await interaction.response.send_message(
                    TEXT["request_category_limit"][lang].format(
                        player=player.mention,
                        category=CATEGORY_LABELS[item_category][lang],
                        items=items_list,
                    ),
                )
                return

        db.add_item_request(
            discord_id=player.id,
            player_name=player.display_name,
            item_name=item_key,
            quantity=quantity,
            thread_id=interaction.channel.id,
            thread_channel_id=interaction.channel.parent_id,
        )

        await interaction.response.send_message(
            TEXT["request_created"][lang].format(
                player=player.mention,
                item=FIXED_ITEMS[item_key][lang],
                qty=quantity
            )
        )

    # ==========================================================
    # UPDATE
    # ==========================================================

    @app_commands.command(
        name="request_update",
        description="Registra atualização (print) do request da thread"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def request_update(self, interaction: discord.Interaction):
        self.ensure_thread(interaction)

        request = db.get_item_request_by_thread(interaction.channel.id)
        lang = (
            self.get_player_language(request[1])
            if request
            else "pt"
        )
        ok = db.update_item_request_by_thread(interaction.channel.id)

        if not ok:
            await interaction.response.send_message(
                TEXT["request_not_found"][lang],
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            TEXT["request_updated"][lang]
        )

    # ==========================================================
    # ENTREGA
    # ==========================================================

    @app_commands.command(
        name="request_delivery",
        description="Registra entrega parcial ou total do item"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.describe(
        item="Item a entregar (apenas requests ativos nesta thread)",
        quantity="Quantidade entregue"
    )
    @app_commands.autocomplete(item=active_thread_item_autocomplete)
    async def request_delivery(
        self,
        interaction: discord.Interaction,
        item: str,
        quantity: int
    ):
        self.ensure_thread(interaction)
        request = db.get_item_request_by_thread(interaction.channel.id)
        lang = (
            self.get_player_language(request[1])
            if request
            else "pt"
        )

        if quantity <= 0:
            await interaction.response.send_message(
                TEXT["qty_invalid"][lang],
                ephemeral=True
            )
            return

        item_key = item

        ok = db.deliver_item_by_thread(
            interaction.channel.id,
            item_key,
            quantity
        )

        if not ok:
            await interaction.response.send_message(
                TEXT["request_not_found"][lang],
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            TEXT["deliver_ok"][lang].format(qty=quantity)
        )

    # ==========================================================
    # RANK
    # ==========================================================

    @app_commands.command(
        name="request_rank",
        description="Mostra o ranking atual de um item"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.choices(item=ITEM_CHOICES)
    async def request_rank(
        self,
        interaction: discord.Interaction,
        item: app_commands.Choice[str]
    ):
        item_key = item.value
        rows = db.get_daily_item_summary()

        filtered = [r for r in rows if r[0] == item_key]

        if not filtered:
            await interaction.response.send_message(
                TEXT["rank_empty"][lang],
                ephemeral=True
            )
            return

        msg = TEXT["rank_header"][lang].format(
            item=FIXED_ITEMS[item_key][lang]
        ) + "\n\n"

        for _, rank, player, remaining, thread_id in filtered:
            thread = self.bot.get_channel(thread_id)
            link = thread.jump_url if thread else ""

            msg += TEXT["rank_line"][lang].format(
                rank=rank,
                player=player,
                remaining=remaining,
                link=link
            ) + "\n"

        await interaction.response.send_message(msg)

    # ==========================================================
    # INFO
    # ==========================================================

    @app_commands.command(
        name="request_info",
        description="Mostra informações do request da thread atual"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def request_info(self, interaction: discord.Interaction):
        self.ensure_thread(interaction)

        req = db.get_item_request_by_thread(interaction.channel.id)

        if not req:
            await interaction.response.send_message(
                TEXT["request_not_found"][lang],
                ephemeral=True
            )
            return

        (
            request_id,
            discord_id,
            player_name,
            item_key,
            rank_position,
            _thread_id,
            last_update,
        ) = req
        lang = self.get_player_language(discord_id)

        # 🔥 NORMALIZA TIMESTAMP AQUI
        last_update = self.normalize_last_update(request_id, last_update)

        days_idle = int((time.time() - last_update) / 86400)

        await interaction.response.send_message(
            TEXT["request_info"][lang].format(
                player=player_name,
                item=FIXED_ITEMS[item_key][lang],
                rank=rank_position,
                days=days_idle,
                link=interaction.channel.jump_url
            )
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    @app_commands.command(
        name="request_delete",
        description="Remove este request de item"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.describe(
        item="Item a remover (apenas requests ativos nesta thread)",
        confirm="Confirme para remover o request"
    )
    @app_commands.autocomplete(item=active_thread_item_autocomplete)
    async def request_delete(
        self,
        interaction: discord.Interaction,
        item: str,
        confirm: bool
    ):
        thread = interaction.channel
        item_key = item
        default_lang = "pt"

        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                TEXT["request_delete_thread_only"][default_lang],
                ephemeral=True
            )
            return

        req = db.get_request_by_thread(thread.id, item_key)
        request_lang = self.get_player_language(req[1]) if req else default_lang

        if not req:
            await interaction.response.send_message(
                TEXT["request_delete_not_linked"][request_lang],
                ephemeral=True
            )
            return

        if not confirm:
            await interaction.response.send_message(
                TEXT["request_delete_confirm_required"][request_lang],
                ephemeral=True
            )
            return

        request_id, _discord_id, item_name, _rank = req

        db.delete_request(request_id)
        db.reorder_item_ranks(item_name)

        await interaction.response.send_message(
            TEXT["request_delete_ok"][request_lang].format(item=item_name)
        )

        try:
            await thread.send(
                TEXT["request_delete_thread_msg"][request_lang]
            )
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ItemRequests(bot))
