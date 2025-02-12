import asyncio
import logging
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
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

# Conversation states
WAITING_FOR_CITY = 1
WAITING_FOR_TIMEZONE = 2

class Bot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.bot = self.app.bot
        
    def send_message_sync(self, chat_id: int, text: str):
        """Synchronous version of send_message."""
        async def _send():
            await self.bot.send_message(chat_id=chat_id, text=text)
        
        # Create event loop if there isn't one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        loop.run_until_complete(_send())

# Keyboard layouts
def get_main_keyboard():
    """Get the main keyboard layout."""
    return ReplyKeyboardMarkup([
        ['🏙 Imposta Città', '🕒 Imposta Fuso Orario']
    ], resize_keyboard=True)

async def check_access(update: Update) -> bool:
    """Check if user has access to the bot."""
    user_id = update.effective_user.id
    return db.check_access(user_id)

async def handle_unauthorized(update: Update):
    """Handle unauthorized access attempt."""
    await update.message.reply_text(
        "Mi dispiace, non hai accesso a questo bot. Contatta l'amministratore.",
        reply_markup=ReplyKeyboardRemove()
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    if not await check_access(update):
        await handle_unauthorized(update)
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Check if user exists
    user = db.get_user(user_id)
    if user:
        await update.message.reply_text(
            f"Bentornato!\n"
            f"La tua città attuale è {user.city}\n"
            f"Il tuo fuso orario è {user.timezone}\n\n"
            "Usa i pulsanti sotto per modificare le impostazioni.",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Benvenuto! Per iniziare, usa il pulsante 'Imposta Città' per selezionare la tua città.",
            reply_markup=get_main_keyboard()
        )

async def start_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the city input conversation."""
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Per favore, invia il nome della città (es. Roma, Milano, Napoli):",
        reply_markup=ReplyKeyboardRemove()
    )
    return WAITING_FOR_CITY

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the city input."""
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    
    city = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Add or update user
    user = db.get_user(user_id)
    timezone = user.timezone if user else 'Europe/Rome'
    db.add_user(user_id, username, city, timezone)
    
    await update.message.reply_text(
        f"Ho impostato la tua città a {city}.\n"
        "Riceverai notifiche ogni giorno alle 7:00 del tuo fuso orario se ci sono partite nella tua città!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def start_timezone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the timezone input conversation."""
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    
    # Create a keyboard with common European timezones
    common_timezones = [
        ['Europe/Rome', 'Europe/London'],
        ['Europe/Paris', 'Europe/Berlin'],
        ['Europe/Madrid', 'Europe/Amsterdam']
    ]
    
    timezone_keyboard = ReplyKeyboardMarkup(common_timezones, resize_keyboard=True)
    
    await update.message.reply_text(
        "Seleziona il tuo fuso orario o invialo manualmente (es. Europe/Rome):",
        reply_markup=timezone_keyboard
    )
    return WAITING_FOR_TIMEZONE

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the timezone input."""
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    
    timezone_str = update.message.text
    
    # Validate timezone
    try:
        pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            "Fuso orario non valido. Per favore, riprova con un fuso orario valido (es. Europe/Rome):",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_TIMEZONE
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if user:
        db.update_user_timezone(user_id, timezone_str)
        city = user.city
    else:
        # If user doesn't exist yet, create with default city
        username = update.effective_user.username
        city = "da impostare"
        db.add_user(user_id, username, city, timezone_str)
    
    await update.message.reply_text(
        f"Ho impostato il tuo fuso orario a {timezone_str}.\n"
        "Riceverai notifiche alle 7:00 del tuo fuso orario!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def handle_invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle timeout or invalid input."""
    await update.message.reply_text(
        "Operazione annullata. Usa i pulsanti sotto per riprovare.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

def run_bot():
    """Run the bot."""
    # Create the Bot instance
    config.BOT = Bot(config.TELEGRAM_BOT_TOKEN)

    # Create conversation handler for city setting
    city_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^🏙 Imposta Città$'), start_city_input),
        ],
        states={
            WAITING_FOR_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)],
        },
        fallbacks=[MessageHandler(filters.ALL, handle_invalid_input)],
    )

    # Create conversation handler for timezone setting
    timezone_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^🕒 Imposta Fuso Orario$'), start_timezone_input),
        ],
        states={
            WAITING_FOR_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_timezone)],
        },
        fallbacks=[MessageHandler(filters.ALL, handle_invalid_input)],
    )

    # Add handlers
    config.BOT.app.add_handler(city_conv_handler)
    config.BOT.app.add_handler(timezone_conv_handler)

    # Initialize and start the scheduler
    scheduler = MatchScheduler(config.BOT.bot)
    scheduler.start()

    # Run the bot
    config.BOT.app.run_polling(allowed_updates=Update.ALL_TYPES)

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