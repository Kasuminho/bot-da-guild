import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, Select, TextInput, View

import db
from config import ANNOUNCEMENTS_CHANNEL_ID, G3X_ROLE_ID

# ==========================================================
# TIMEZONES DISPONÍVEIS
# ==========================================================
TIMEZONES = {
    "🇧🇷 Brasil (America/Sao_Paulo)": "America/Sao_Paulo",
    "🌍 UTC": "UTC",
}


# ==========================================================
# MODAL – DATA/HORA
# ==========================================================
class ReminderDateTimeModal(Modal, title="Cadastrar lembrete"):
    datetime_input = TextInput(
        label="Data e hora",
        placeholder="YYYY-MM-DD HH:MM",
        required=True,
    )

    def __init__(self, cog, tipo: str, nome: str, tz_name: str):
        super().__init__()
        self.cog = cog
        self.tipo = tipo
        self.nome = nome
        self.tz_name = tz_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tz = ZoneInfo(self.tz_name)

            local_dt = datetime.strptime(
                self.datetime_input.value, "%Y-%m-%d %H:%M"
            ).replace(tzinfo=tz)

            utc_dt = local_dt.astimezone(timezone.utc)
            timestamp = int(utc_dt.timestamp())

        except ValueError:
            await interaction.response.send_message(
                "❌ Formato inválido. Use `YYYY-MM-DD HH:MM`",
                ephemeral=True,
            )
            return

        if timestamp <= int(time.time()):
            await interaction.response.send_message(
                "❌ A data precisa ser no futuro.",
                ephemeral=True,
            )
            return

        await self.cog.create_reminder(
            interaction=interaction,
            tipo=self.tipo,
            nome=self.nome,
            timestamp=timestamp,
            tz_name=self.tz_name,
        )


# ==========================================================
# SELECT – TIMEZONE
# ==========================================================
class TimezoneSelect(Select):
    def __init__(self, cog, tipo: str, nome: str):
        super().__init__(
            placeholder="Selecione o fuso horário",
            options=[
                discord.SelectOption(label=label, value=tz)
                for label, tz in TIMEZONES.items()
            ],
        )
        self.cog = cog
        self.tipo = tipo
        self.nome = nome

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            ReminderDateTimeModal(
                cog=self.cog,
                tipo=self.tipo,
                nome=self.nome,
                tz_name=self.values[0],
            )
        )


class TimezoneView(View):
    def __init__(self, cog, tipo: str, nome: str):
        super().__init__(timeout=60)
        self.add_item(TimezoneSelect(cog, tipo, nome))


# ==========================================================
# COG
# ==========================================================
class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    # -------------------------
    # SLASH – CADASTRAR
    # -------------------------
    @app_commands.command(
        name="cadastrarlembrete",
        description="Cadastrar lembrete com avisos automáticos",
    )
    async def cadastrarlembrete(
        self,
        interaction: discord.Interaction,
        tipo: str,
        nome: str,
    ):
        await interaction.response.send_message(
            "🌍 Selecione o fuso horário do evento:",
            view=TimezoneView(self, tipo, nome),
            ephemeral=True,
        )

    # -------------------------
    # CRIAÇÃO REAL
    # -------------------------
    async def create_reminder(
        self,
        interaction: discord.Interaction,
        tipo: str,
        nome: str,
        timestamp: int,
        tz_name: str,
    ):
        db.add_reminder(
            tipo=tipo,
            nome=nome,
            channel_id=ANNOUNCEMENTS_CHANNEL_ID,
            timestamp=timestamp,
        )

        channel = self.bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if channel:
            await channel.send(
                f"<@&{G3X_ROLE_ID}>\n"
                f"📢 **Novo lembrete cadastrado**\n\n"
                f"📌 {tipo}: {nome}\n"
                f"🌍 Timezone: No seu horário local que mostra no computador/celular\n"
                f"🌍 Timezone: On your local time where show on computer/cellphone\n"
                f"⏰ <t:{timestamp}:F>\n\n"
                f"🔔 Avisos automáticos:\n"
                f"• 1 hora antes\n"
                f"• 30 minutos antes\n"
                f"• Na hora"
            )

        # ⚠️ AQUI É A CORREÇÃO PRINCIPAL
        await interaction.response.send_message(
            "✅ Lembrete cadastrado com sucesso.",
            ephemeral=True,
        )

    # -------------------------
    # LOOP AUTOMÁTICO
    # -------------------------
    @tasks.loop(seconds=60)
    async def reminder_loop(self):
        now = int(time.time())
        reminders = db.get_active_reminders()

        for r in reminders:
            (
                reminder_id,
                tipo,
                nome,
                channel_id,
                timestamp,
                _,
                warned_1h,
                warned_30m,
                warned_now,
            ) = r

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            if not warned_1h and now >= timestamp - 3600:
                await channel.send(
                    f"<@&{G3X_ROLE_ID}>\n"
                    f"⏳ **Falta 1 hora** — {tipo}: {nome}\n"
                    f"⏰ <t:{timestamp}:F>"
                )
                db.mark_warned(reminder_id, "warned_1h")

            elif not warned_30m and now >= timestamp - 1800:
                await channel.send(
                    f"<@&{G3X_ROLE_ID}>\n"
                    f"⏳ **Faltam 30 minutos** — {tipo}: {nome}\n"
                    f"⏰ <t:{timestamp}:F>"
                )
                db.mark_warned(reminder_id, "warned_30m")

            elif not warned_now and now >= timestamp:
                await channel.send(
                    f"<@&{G3X_ROLE_ID}>\n"
                    f"⏰ **Agora** — {tipo}: {nome}\n"
                    f"⏰ <t:{timestamp}:F>"
                )
                db.mark_warned(reminder_id, "warned_now")
                db.mark_reminder_sent(reminder_id)


async def setup(bot):
    await bot.add_cog(Reminders(bot))
