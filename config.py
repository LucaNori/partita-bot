"""Configuration management for environment variables"""
import os
from dotenv import load_dotenv

load_dotenv()

# Application settings
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Rome')

# API Tokens
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
FOOTBALL_API_TOKEN = os.getenv('FOOTBALL_API_TOKEN')

# Admin interface settings
ADMIN_PORT = int(os.getenv('ADMIN_PORT', '5000'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
