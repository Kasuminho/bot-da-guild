import discord
from discord.ui import Select, View

import db

TIMEZONES = [
    ("🇺🇸 Baker Island", "Etc/GMT+12"),
    ("🇺🇸 Samoa", "Pacific/Pago_Pago"),
    ("🇺🇸 Honolulu", "Pacific/Honolulu"),
    ("🇺🇸 Anchorage", "America/Anchorage"),
    ("🇺🇸 Los Angeles", "America/Los_Angeles"),
    ("🇺🇸 Denver", "America/Denver"),
    ("🇺🇸 Chicago", "America/Chicago"),
    ("🇺🇸 New York", "America/New_York"),
    ("🇨🇦 Halifax", "America/Halifax"),
    ("🇧🇷 São Paulo", "America/Sao_Paulo"),
    ("🇧🇷 Fernando de Noronha", "America/Noronha"),
    ("🇵🇹 Azores", "Atlantic/Azores"),
    ("🇬🇧 London", "Europe/London"),
    ("🇩🇪 Berlin", "Europe/Berlin"),
    ("🇬🇷 Athens", "Europe/Athens"),
    ("🇷🇺 Moscow", "Europe/Moscow"),
    ("🇦🇪 Dubai", "Asia/Dubai"),
    ("🇵🇰 Karachi", "Asia/Karachi"),
    ("🇧🇩 Dhaka", "Asia/Dhaka"),
    ("🇹🇭 Bangkok", "Asia/Bangkok"),
    ("🇨🇳 Beijing", "Asia/Shanghai"),
    ("🇯🇵 Tokyo", "Asia/Tokyo"),
    ("🇦🇺 Sydney", "Australia/Sydney"),
    ("🇳🇿 Auckland", "Pacific/Auckland"),
]


class TimezoneSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="🌍 Escolha sua cidade (uma vez só)",
            options=[discord.SelectOption(label=label, value=value) for label, value in TIMEZONES],
        )

    async def callback(self, interaction: discord.Interaction):
        db.set_player_timezone(interaction.user.id, self.values[0])
        await interaction.response.send_message("✅ Cidade salva. Nunca mais pergunto 😉", ephemeral=True)


class TimezoneView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(TimezoneSelect())
