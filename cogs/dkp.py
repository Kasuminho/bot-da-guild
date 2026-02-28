from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID
from core.context import TenantContext
from core.feature_gate import requires_feature
from core.permissions import is_guild_admin_or_officer
from repositories.audit_repository import AuditRepository
from repositories.dkp_repository import DKPRepository
from repositories.guild_config_repository import GuildConfigRepository
from repositories.saas_repository import SaaSRepository
from services.dkp_service import DKPService
from services.feature_service import FeatureService
from services.guild_config_service import GuildConfigService

VALID_LOOT_MODES = {"legacy", "dkp"}
VALID_DKP_CONFIG_KEYS = {"min_bid", "allow_negative", "bid_timeout", "tie_breaker"}


class DKPCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.audit_repo = AuditRepository()
        self.dkp_service = DKPService(DKPRepository(), self.audit_repo)
        self.feature_service = FeatureService(SaaSRepository())
        self.config_service = GuildConfigService(GuildConfigRepository(), self.audit_repo)

        self.dkp_group = app_commands.Group(name="dkp", description="DKP commands")
        self.loot_group = app_commands.Group(name="loot", description="Loot mode commands")

        self.dkp_group.add_command(self.add)
        self.dkp_group.add_command(self.remove)
        self.dkp_group.add_command(self.decay)
        self.dkp_group.add_command(self.reset)
        self.dkp_group.add_command(self.balance)
        self.dkp_group.add_command(self.top)
        self.dkp_group.add_command(self.history)
        self.dkp_group.add_command(self.config_set)

        self.loot_group.add_command(self.mode_set)

        self.bot.tree.add_command(self.dkp_group)
        self.bot.tree.add_command(self.loot_group)

    def cog_unload(self):
        self.bot.tree.remove_command(self.dkp_group.name, type=self.dkp_group.type)
        self.bot.tree.remove_command(self.loot_group.name, type=self.loot_group.type)

    async def _ensure_guild(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Guild-only command.", ephemeral=True)
            return False
        return True

    async def _ensure_staff(self, interaction: discord.Interaction) -> bool:
        if not await self._ensure_guild(interaction):
            return False

        if not is_guild_admin_or_officer(interaction, STAFF_ROLE_ID):
            await interaction.response.send_message("Admin/staff only command.", ephemeral=True)
            return False

        return True

    @staticmethod
    def _ctx(interaction: discord.Interaction) -> TenantContext:
        if interaction.guild is None:
            raise RuntimeError("Tenant context requested outside guild interaction")

        return TenantContext(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel_id,
            actor_user_id=interaction.user.id,
        )

    @staticmethod
    def _parse_config_value(raw: str):
        normalized = raw.strip()
        lowered = normalized.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if normalized.isdigit():
            return int(normalized)
        return normalized

    @app_commands.command(name="add", description="Add DKP points")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def add(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str):
        if not await self._ensure_staff(interaction):
            return

        self.dkp_service.add_points(self._ctx(interaction), user.id, amount, reason)
        await interaction.response.send_message(
            f"Added **{abs(amount)}** DKP to {user.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Remove DKP points")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def remove(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str):
        if not await self._ensure_staff(interaction):
            return

        self.dkp_service.remove_points(self._ctx(interaction), user.id, amount, reason)
        await interaction.response.send_message(
            f"Removed **{abs(amount)}** DKP from {user.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="decay", description="Apply DKP decay percent")
    @requires_feature("dkp_decay", lambda s: s.feature_service)
    async def decay(self, interaction: discord.Interaction, percent: int):
        if not await self._ensure_staff(interaction):
            return

        if percent <= 0 or percent > 100:
            await interaction.response.send_message("Percent must be between 1 and 100.", ephemeral=True)
            return

        self.dkp_service.apply_decay(self._ctx(interaction), percent)
        await interaction.response.send_message(f"Decay **{percent}%** applied.", ephemeral=True)

    @app_commands.command(name="reset", description="Reset DKP ledger. Use confirm=true")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def reset(self, interaction: discord.Interaction, confirm: bool = False):
        if not await self._ensure_staff(interaction):
            return

        if not confirm:
            await interaction.response.send_message("Run `/dkp reset confirm:true` to confirm.", ephemeral=True)
            return

        self.dkp_service.reset(self._ctx(interaction))
        await interaction.response.send_message("DKP reset completed.", ephemeral=True)

    @app_commands.command(name="balance", description="View DKP balance")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def balance(self, interaction: discord.Interaction, user: discord.Member | None = None):
        if not await self._ensure_guild(interaction):
            return

        target = user or interaction.user
        balance = self.dkp_service.get_balance(self._ctx(interaction), target.id)
        await interaction.response.send_message(f"{target.mention} has **{balance}** DKP.", ephemeral=True)

    @app_commands.command(name="top", description="DKP leaderboard")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def top(self, interaction: discord.Interaction, limit: int = 10):
        if not await self._ensure_guild(interaction):
            return

        bounded_limit = max(1, min(limit, 25))
        rows = self.dkp_service.get_leaderboard(self._ctx(interaction), bounded_limit)
        lines = [f"{idx}. <@{user_id}> — **{score}**" for idx, (user_id, score) in enumerate(rows, start=1)]
        await interaction.response.send_message("\n".join(lines) if lines else "No DKP data.", ephemeral=True)

    @app_commands.command(name="history", description="DKP history")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def history(self, interaction: discord.Interaction, user: discord.Member | None = None, limit: int = 20):
        if not await self._ensure_guild(interaction):
            return

        target = user or interaction.user
        bounded_limit = max(1, min(limit, 50))
        rows = self.dkp_service.get_history(self._ctx(interaction), target.id, bounded_limit)
        lines = [f"{amount:+} | {reason} | by <@{created_by}> | ts={created_at}" for amount, reason, created_by, created_at in rows]
        await interaction.response.send_message("\n".join(lines) if lines else "No history.", ephemeral=True)

    @app_commands.command(name="config_set", description="Set DKP configuration key")
    @requires_feature("dkp_enabled", lambda s: s.feature_service)
    async def config_set(self, interaction: discord.Interaction, key: str, value: str):
        if not await self._ensure_staff(interaction):
            return

        normalized_key = key.strip()
        if normalized_key not in VALID_DKP_CONFIG_KEYS:
            await interaction.response.send_message("Invalid config key.", ephemeral=True)
            return

        parsed_value = self._parse_config_value(value)
        self.config_service.set_config(
            interaction.guild.id,
            interaction.user.id,
            f"dkp_{normalized_key}",
            parsed_value,
        )
        await interaction.response.send_message(f"DKP config `{normalized_key}` updated.", ephemeral=True)

    @app_commands.command(name="mode_set", description="Set loot mode (legacy|dkp)")
    async def mode_set(self, interaction: discord.Interaction, mode: str):
        if not await self._ensure_staff(interaction):
            return

        normalized_mode = mode.lower().strip()
        if normalized_mode not in VALID_LOOT_MODES:
            await interaction.response.send_message("Invalid mode. Use legacy or dkp.", ephemeral=True)
            return

        if normalized_mode == "dkp" and not self.feature_service.can_use_feature(interaction.guild.id, "dkp_enabled"):
            await interaction.response.send_message("DKP mode is not enabled on current plan.", ephemeral=True)
            return

        self.config_service.set_config(interaction.guild.id, interaction.user.id, "loot_mode", normalized_mode)
        await interaction.response.send_message(f"Loot mode set to **{normalized_mode}**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DKPCog(bot))
