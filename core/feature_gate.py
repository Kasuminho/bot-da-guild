from collections.abc import Callable
from functools import wraps

import discord

from core.context import TenantContext


def requires_feature(feature_key: str, service_getter: Callable[[object], object]):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command can only be used inside a guild.",
                    ephemeral=True,
                )
                return

            ctx = TenantContext(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel_id,
                actor_user_id=interaction.user.id,
            )
            feature_service = service_getter(self)
            if not feature_service.can_use_feature(ctx.guild_id, feature_key):
                await interaction.response.send_message(
                    f"Feature `{feature_key}` is not available on your current plan. Ask an admin to upgrade.",
                    ephemeral=True,
                )
                return

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator
