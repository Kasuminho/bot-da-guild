# Exemplo de configuração — NÃO comitar tokens reais.
# Copie para config.py ou use variáveis de ambiente (.env) no desenvolvimento.

import os

from dotenv import load_dotenv

load_dotenv()
# Se usar python-dotenv, carregue .env no início do seu bot:
# from dotenv import load_dotenv
# load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "coloque_o_token_aqui")
DATABASE_URL = os.getenv("DATABASE_URL", "")  # ex: postgres://user:pass@host:5432/db
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
CATEGORY_ID = int(os.getenv("CATEGORY_ID", "0"))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID", "0"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID", "0"))
FORUM_TAG_ID = int(os.getenv("FORUM_TAG_ID", "0"))
G3X_ROLE_ID = int(os.getenv("G3X_ROLE_ID", "0"))
EXTRAORDINARY_STAFF_CHANNEL_ID = int(
    os.getenv("EXTRAORDINARY_STAFF_CHANNEL_ID", "0")
)

EXTRAORDINARY_STAFF_WEBHOOK_URL = os.getenv(
    "EXTRAORDINARY_STAFF_WEBHOOK_URL", ""
)

FORUM_ANNOUNCE_TEST_MODE = os.getenv("FORUM_ANNOUNCE_TEST_MODE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

IMAGE_STORAGE_PROVIDER = os.getenv("IMAGE_STORAGE_PROVIDER", "local")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
