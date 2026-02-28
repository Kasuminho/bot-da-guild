import logging
import sys

LOG_FILE = "bot.log"


def setup_global_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="ts=%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),  # CMD
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )

    # Captura logs do discord.py
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    # Redireciona print() para logging
    sys.stdout = StreamToLogger(logging.getLogger("STDOUT"), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger("STDERR"), logging.ERROR)

    # Captura exceções globais
    sys.excepthook = handle_exception


class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass


def handle_exception(exc_type, exc_value, exc_traceback):
    logging.critical(
        "EXCEÇÃO NÃO TRATADA",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
