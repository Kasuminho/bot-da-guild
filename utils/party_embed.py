import discord


def build_party_embed(reason_pt, reason_en, start_ts, end_ts, creator, members):
    embed = discord.Embed(
        title="🎉 Party",
        description=f"**{reason_pt}**\n*{reason_en}*",
        color=discord.Color.green(),
    )

    embed.add_field(
        name="🕒 Disponibilidade / Availability",
        value=f"<t:{start_ts}:t> – <t:{end_ts}:t>",
        inline=False,
    )

    slots = members + ["—"] * (5 - len(members))

    embed.add_field(
        name=f"👥 Party ({len(members)}/5)", value="\n".join(slots), inline=False
    )

    embed.set_footer(text=f"Criador: {creator.display_name}")

    return embed
