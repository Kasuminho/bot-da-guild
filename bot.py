import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID, TOKEN
from logger import setup_global_logger

# ==========================================================
# LOGGER GLOBAL
# ==========================================================
setup_global_logger()
log = logging.getLogger("bot.commands")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/health", "/healthz"}:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    host = os.getenv("HEALTH_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "10000"))
    server = ThreadingHTTPServer((host, port), HealthHandler)

    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Healthcheck ativo em http://%s:%s/health", host, port)

# ==========================================================
# INTENTS
# ==========================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# ==========================================================
# BOT
# ==========================================================
bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================================
# ON MESSAGE (fluxos de imagem + prefix commands)
# ==========================================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    flow = getattr(bot, "pending_image_flows", {}).get(message.author.id)

    if flow and message.attachments:
        for attachment in message.attachments:
            flow.images.append(attachment)

        if len(flow.images) >= 2:
            flow.images = flow.images[:2]
            del bot.pending_image_flows[message.author.id]
            await flow.ask_category()

    await bot.process_commands(message)


# ==========================================================
# LOG SLASH COMMANDS
# ==========================================================
@bot.event
async def on_app_command_completion(
    interaction: discord.Interaction,
    command: discord.app_commands.Command,
):
    user = interaction.user
    guild = interaction.guild
    channel = interaction.channel

    log.info(
        "SLASH | /%s | user=%s (%s) | guild=%s (%s) | channel=%s (%s)",
        command.qualified_name,
        user,
        user.id,
        guild.name if guild else "DM",
        guild.id if guild else "DM",
        channel.name if hasattr(channel, "name") else "DM",
        channel.id if channel else "DM",
    )


# ==========================================================
# LOG PREFIX COMMANDS
# ==========================================================
@bot.event
async def on_command_completion(ctx: commands.Context):
    log.info(
        "PREFIX | %s | user=%s (%s) | guild=%s (%s) | channel=%s (%s)",
        ctx.command.qualified_name,
        ctx.author,
        ctx.author.id,
        ctx.guild.name if ctx.guild else "DM",
        ctx.guild.id if ctx.guild else "DM",
        ctx.channel.name,
        ctx.channel.id,
    )


# ==========================================================
# LOG ERROS DE SLASH COMMAND
# ==========================================================
@bot.event
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError,
):
    log.error(
        "SLASH ERROR | user=%s (%s) | command=%s | error=%r",
        interaction.user,
        interaction.user.id,
        interaction.command.qualified_name if interaction.command else "UNKNOWN",
        error,
        exc_info=True,
    )


# ==========================================================
# READY
# ==========================================================

COG_EXTENSIONS = [
    "cogs.players",
    "cogs.reminders",
    "cogs.scheduler",
    "cogs.forum_announce",
    "cogs.forum_delivery",
    "cogs.party_events",
    "cogs.party",
    "cogs.daily_announcement",
    "cogs.player_progress",
    "cogs.cadastrar_item",
    "cogs.rotation_eligibility",
    "cogs.item_requests",
    "cogs.item_requests_scheduler",
    "cogs.item_requests_admin",
]


async def load_cogs_once():
    for extension in COG_EXTENSIONS:
        if extension in bot.extensions:
            continue
        try:
            await bot.load_extension(extension)
            log.info("Cog carregada: %s", extension)
        except commands.ExtensionError:
            log.exception("Falha ao carregar cog: %s", extension)


@bot.event
async def on_ready():
    # Cogs
    await load_cogs_once()

    # Fluxos temporários
    bot.pending_image_flows = {}

    # Sync slash commands
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    print(f"Bot online como {bot.user}")
    

# ==========================================================
# RUN
# ==========================================================
start_health_server()
bot.run(TOKEN)
