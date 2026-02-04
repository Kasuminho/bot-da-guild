import time
import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID
import db
from utils.i18n import TEXT
from utils.fixed_items import FIXED_ITEMS, ITEM_CHOICES

lang = "pt"


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

        if quantity <= 0:
            await interaction.response.send_message(
                TEXT["qty_invalid"][lang],
                ephemeral=True
            )
            return

        item_key = item.value

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
        name="request_deliver",
        description="Registra entrega parcial ou total do item"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.describe(
        item="Item a Entregar",
        quantity="Quantidade total desejada"
    )
    @app_commands.choices(item=ITEM_CHOICES)
    async def request_deliver(
        self,
        interaction: discord.Interaction,
        item: app_commands.Choice[str],
        quantity: int
    ):
        self.ensure_thread(interaction)

        if quantity <= 0:
            await interaction.response.send_message(
                TEXT["qty_invalid"][lang],
                ephemeral=True
            )
            return

        item_key = item.value

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
            _discord_id,
            player_name,
            item_key,
            rank_position,
            _thread_id,
            last_update,
        ) = req

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
        description="Remove this item request"
    )
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    @app_commands.choices(item=ITEM_CHOICES)
    async def request_delete(
        self,
        interaction: discord.Interaction,
        item: app_commands.Choice[str]
    ):
        thread = interaction.channel
        item_key = item.value

        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                "❌ Use this command inside the request thread.",
                ephemeral=True
            )
            return

        req = db.get_request_by_thread(thread.id, item_key)

        if not req:
            await interaction.response.send_message(
                "❌ This thread is not linked to any request.",
                ephemeral=True
            )
            return

        request_id, item_name, rank = req

        db.delete_request(request_id)
        db.reorder_item_ranks(item_name)

        await interaction.response.send_message(
            f"🗑️ Request for **{item_name}** removed successfully."
        )

        try:
            await thread.send(
                f"🗑️ This request was removed from the rank."
            )
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ItemRequests(bot))
