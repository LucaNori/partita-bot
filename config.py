import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

load_dotenv()

# Convert DEBUG string to boolean
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Load timezone (default to Europe/Rome)
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Rome')
# If invalid timezone is specified, fallback to Europe/Rome
try:
    TIMEZONE_INFO = ZoneInfo(TIMEZONE)
except ZoneInfoNotFoundError:
    logger.warning(f"Invalid timezone: {TIMEZONE}. Falling back to Europe/Rome")
    TIMEZONE = 'Europe/Rome'
    TIMEZONE_INFO = ZoneInfo(TIMEZONE)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
FOOTBALL_API_TOKEN = os.getenv('FOOTBALL_API_TOKEN')
ADMIN_PORT = int(os.getenv('ADMIN_PORT', '5000'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

BOT = None
