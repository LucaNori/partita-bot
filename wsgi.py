import config
from admin import app as application
from bot_manager import get_bot

# Initialize bot instance before the Flask app starts
bot_instance = get_bot(config.TELEGRAM_BOT_TOKEN)

if __name__ == "__main__":
    application.run()
