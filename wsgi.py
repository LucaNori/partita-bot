import config
from admin import app as application
from bot_manager import is_bot_initialized, get_bot
import logging

logger = logging.getLogger(__name__)

# Only initialize if not already done
# This ensures WSGI server will have a proper bot instance if needed
if not is_bot_initialized():
    logger.info("Initializing bot in WSGI app (bot not initialized elsewhere)")
    get_bot(config.TELEGRAM_BOT_TOKEN)
else:
    logger.info("Bot already initialized, not reinitializing in WSGI app")

if __name__ == "__main__":
    application.run()
