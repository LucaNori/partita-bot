import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Admin Interface Configuration
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change_this_password')
ADMIN_PORT = int(os.getenv('ADMIN_PORT', 5000))

# Scheduler Configuration
NOTIFICATION_HOUR = 7  # Hour of the day when notifications are sent (24-hour format)
NOTIFICATION_MINUTE = 0  # Minute of the hour when notifications are sent

# Database Configuration
DATABASE_PATH = os.path.join('data', 'bot.sqlite3')

# Football Data API Configuration
FOOTBALL_API_TOKEN = os.getenv('FOOTBALL_API_TOKEN')
if not FOOTBALL_API_TOKEN:
    raise ValueError("FOOTBALL_API_TOKEN not found in environment variables")

FOOTBALL_API_BASE_URL = "http://api.football-data.org/v4"
FOOTBALL_API_HEADERS = {
    'X-Auth-Token': FOOTBALL_API_TOKEN
}