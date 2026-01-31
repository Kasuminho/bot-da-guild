# Exemplo de configuração — NÃO comitar tokens reais.
# Copie para config.py ou use variáveis de ambiente (.env) no desenvolvimento.

import os
from dotenv import load_dotenv

load_dotenv()
# Se usar python-dotenv, carregue .env no início do seu bot:
# from dotenv import load_dotenv
# load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "coloque_o_token_aqui")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite:///data.db"
)  # ex: postgres://user:pass@host:5432/db
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0"))
CATEGORY_ID = int(os.getenv("CATEGORY_ID", "0"))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID", "0"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID", "0"))
FORUM_TAG_ID = int(os.getenv("FORUM_TAG_ID", "0"))
G3X_ROLE_ID = int(os.getenv("G3X_ROLE_ID", "0"))
STAFF_CHANNEL_ID = int(os.getenv("STAFF_CHANNEL_ID", "0"))
ITEM_REQUEST_SUMMARY_CHANNEL_ID = int(os.getenv("ITEM_REQUEST_SUMMARY_CHANNEL_ID", "0"))