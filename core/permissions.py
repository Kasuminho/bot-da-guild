import discord


def is_guild_admin_or_officer(interaction: discord.Interaction, staff_role_id: int) -> bool:
    if interaction.guild is None:
        return False

    member = interaction.user
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True

    if staff_role_id and any(role.id == staff_role_id for role in member.roles):
        return True

    return False
