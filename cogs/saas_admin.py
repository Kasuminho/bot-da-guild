from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID
from core.permissions import is_guild_admin_or_officer
from repositories.audit_repository import AuditRepository
from repositories.saas_repository import SaaSRepository
from services.saas_service import SaaSService

VALID_PLANS = {"free", "pro", "elite"}
VALID_SUBSCRIPTION_STATUS = {"active", "trialing", "canceled", "past_due", "free"}


class SaaSAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = SaaSService(SaaSRepository(), AuditRepository())

        self.group = app_commands.Group(name="saas", description="SaaS admin commands")
        self.group.add_command(self.plan_view)
        self.group.add_command(self.plan_set)
        self.group.add_command(self.subscription_set_status)
        self.group.add_command(self.subscription_set_expiry)
        self.bot.tree.add_command(self.group)

    def cog_unload(self):
        self.bot.tree.remove_command(self.group.name, type=self.group.type)

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Use this command in a guild.", ephemeral=True)
            return False

        if not is_guild_admin_or_officer(interaction, STAFF_ROLE_ID):
            await interaction.response.send_message("Admin/staff only command.", ephemeral=True)
            return False

        self.service.ensure_guild(interaction.guild.id, interaction.guild.name)
        return True

    @app_commands.command(name="plan_view", description="View current plan")
    async def plan_view(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return

        data = self.service.view_plan(interaction.guild.id)
        await interaction.response.send_message(
            f"Plan: **{data['plan_id']}** | Status: **{data['status']}** | Expiry: `{data['expires_at']}`",
            ephemeral=True,
        )

    @app_commands.command(name="plan_set", description="Set guild plan")
    @app_commands.describe(plan="free, pro or elite")
    async def plan_set(self, interaction: discord.Interaction, plan: str):
        if not await self._guard(interaction):
            return

        normalized = plan.lower().strip()
        if normalized not in VALID_PLANS:
            await interaction.response.send_message("Invalid plan. Use free/pro/elite.", ephemeral=True)
            return

        self.service.set_plan(interaction.guild.id, interaction.user.id, normalized)
        await interaction.response.send_message(f"Plan updated to **{normalized}**.", ephemeral=True)

    @app_commands.command(name="subscription_set_status", description="Set subscription status")
    async def subscription_set_status(self, interaction: discord.Interaction, status: str):
        if not await self._guard(interaction):
            return

        normalized = status.lower().strip()
        if normalized not in VALID_SUBSCRIPTION_STATUS:
            await interaction.response.send_message("Invalid status.", ephemeral=True)
            return

        self.service.set_subscription_status(interaction.guild.id, interaction.user.id, normalized)
        await interaction.response.send_message(
            f"Subscription status set to **{normalized}**.",
            ephemeral=True,
        )

    @app_commands.command(name="subscription_set_expiry", description="Set subscription expiry (ISO datetime)")
    async def subscription_set_expiry(self, interaction: discord.Interaction, iso_date: str):
        if not await self._guard(interaction):
            return

        try:
            self.service.set_subscription_expiry(interaction.guild.id, interaction.user.id, iso_date)
        except ValueError:
            await interaction.response.send_message(
                "Invalid date. Use ISO format like 2026-01-31T00:00:00+00:00.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Subscription expiry set to **{iso_date}**.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SaaSAdmin(bot))
