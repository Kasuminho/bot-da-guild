def party_message(reason, start_ts, end_ts, creator):
    return (
        f"🎉 **{reason}**\n\n"
        f"🕒 **Disponibilidade / Availability:**\n"
        f"<t:{start_ts}:t> - <t:{end_ts}:t>\n\n"
        f"👥 **Party:**\n"
        f"- {creator.mention}\n"
        f"- \n"
        f"- \n"
        f"- \n"
        f"- "
    )
