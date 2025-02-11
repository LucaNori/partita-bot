import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from storage import Database
from scheduler import MatchScheduler
from admin import run_admin_interface
import config
import threading

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Check if user has access
    if not db.check_access(user_id):
        await update.message.reply_text(
            "Mi dispiace, non hai accesso a questo bot. Contatta l'amministratore."
        )
        return
    
    # Check if user exists
    user = db.get_user(user_id)
    if user:
        await update.message.reply_text(
            f"Bentornato! La tua città attuale è {user.city}.\n"
            "Usa /setcity per cambiarla."
        )
    else:
        await update.message.reply_text(
            "Benvenuto! Per iniziare, imposta la tua città usando il comando /setcity seguito dal nome della città.\n"
            "Esempio: /setcity Roma"
        )

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /setcity command."""
    user_id = update.effective_user.id
    
    # Check if user has access
    if not db.check_access(user_id):
        await update.message.reply_text(
            "Mi dispiace, non hai accesso a questo bot. Contatta l'amministratore."
        )
        return
    
    # Check if city was provided
    if not context.args:
        await update.message.reply_text(
            "Per favore, specifica una città.\n"
            "Esempio: /setcity Roma"
        )
        return
    
    city = " ".join(context.args)
    username = update.effective_user.username
    
    # Add or update user
    db.add_user(user_id, username, city)
    
    await update.message.reply_text(
        f"Ho impostato la tua città a {city}.\n"
        "Riceverai notifiche ogni giorno alle 7:00 se ci sono partite nella tua città!"
    )

async def check_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /check command to manually check matches."""
    user_id = update.effective_user.id
    
    # Check if user has access
    if not db.check_access(user_id):
        await update.message.reply_text(
            "Mi dispiace, non hai accesso a questo bot. Contatta l'amministratore."
        )
        return
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "Prima devi impostare la tua città usando /setcity"
        )
        return
    
    from fetcher import MatchFetcher
    fetcher = MatchFetcher()
    message = fetcher.check_matches_for_city(user.city)
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = """
Ecco i comandi disponibili:

/start - Avvia il bot
/setcity [città] - Imposta la tua città
/check - Controlla le partite di oggi nella tua città
/help - Mostra questo messaggio di aiuto

Riceverai automaticamente una notifica alle 7:00 se ci sono partite nella tua città!
"""
    await update.message.reply_text(help_text)

def run_bot():
    """Run the bot."""
    # Create the Application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setcity", set_city))
    application.add_handler(CommandHandler("check", check_matches))
    application.add_handler(CommandHandler("help", help_command))

    # Initialize and start the scheduler
    scheduler = MatchScheduler(application.bot)
    scheduler.start()

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Start both the bot and admin interface."""
    # Start admin interface in a separate thread
    admin_thread = threading.Thread(target=run_admin_interface)
    admin_thread.daemon = True
    admin_thread.start()

    # Run the bot in the main thread
    run_bot()

if __name__ == '__main__':
    main()