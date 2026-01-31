import discord
from discord.ui import Select, View

from db import conn, cursor

TIMEZONES = [
    ("🇺🇸 Baker Island", "Etc/GMT+12"),  # UTC-12
    ("🇺🇸 Samoa", "Pacific/Pago_Pago"),  # UTC-11
    ("🇺🇸 Honolulu", "Pacific/Honolulu"),  # UTC-10
    ("🇺🇸 Anchorage", "America/Anchorage"),  # UTC-9
    ("🇺🇸 Los Angeles", "America/Los_Angeles"),  # UTC-8
    ("🇺🇸 Denver", "America/Denver"),  # UTC-7
    ("🇺🇸 Chicago", "America/Chicago"),  # UTC-6
    ("🇺🇸 New York", "America/New_York"),  # UTC-5
    ("🇨🇦 Halifax", "America/Halifax"),  # UTC-4
    ("🇧🇷 São Paulo", "America/Sao_Paulo"),  # UTC-3
    ("🇧🇷 Fernando de Noronha", "America/Noronha"),  # UTC-2
    ("🇵🇹 Azores", "Atlantic/Azores"),  # UTC-1
    ("🇬🇧 London", "Europe/London"),  # UTC+0
    ("🇩🇪 Berlin", "Europe/Berlin"),  # UTC+1
    ("🇬🇷 Athens", "Europe/Athens"),  # UTC+2
    ("🇷🇺 Moscow", "Europe/Moscow"),  # UTC+3
    ("🇦🇪 Dubai", "Asia/Dubai"),  # UTC+4
    ("🇵🇰 Karachi", "Asia/Karachi"),  # UTC+5
    ("🇧🇩 Dhaka", "Asia/Dhaka"),  # UTC+6
    ("🇹🇭 Bangkok", "Asia/Bangkok"),  # UTC+7
    ("🇨🇳 Beijing", "Asia/Shanghai"),  # UTC+8
    ("🇯🇵 Tokyo", "Asia/Tokyo"),  # UTC+9
    ("🇦🇺 Sydney", "Australia/Sydney"),  # UTC+10
    ("🇳🇿 Auckland", "Pacific/Auckland"),  # UTC+12
]


class TimezoneSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="🌍 Escolha sua cidade (uma vez só)",
            options=[
                discord.SelectOption(label=label, value=value)
                for label, value in TIMEZONES
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        tz = self.values[0]

        cursor.execute(
            "UPDATE players SET timezone = ? WHERE discord_id = ?",
            (tz, interaction.user.id),
        )
        conn.commit()

        await interaction.response.send_message(
            "✅ Cidade salva. Nunca mais pergunto 😉",
            ephemeral=True,
        )


class TimezoneView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(TimezoneSelect())
