import nest_asyncio
nest_asyncio.apply()

import asyncio
import logging
import httpx
import os
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from storage import Database
from scheduler import create_scheduler
from admin import run_admin_interface
from bot_manager import get_bot
import config
import threading

# Configure logging based on DEBUG setting
logging_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging_level
)
logger = logging.getLogger(__name__)

# Control httpx logging
httpx_logger = logging.getLogger('httpx')
httpx_logger.setLevel(logging.DEBUG if config.DEBUG else logging.WARNING)

db = Database()

WAITING_FOR_CITY = 1

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ['🏙 Imposta Città']
    ], resize_keyboard=True)

async def check_access(update: Update) -> bool:
    user_id = update.effective_user.id
    return db.check_access(user_id)

async def handle_unauthorized(update: Update):
    await update.message.reply_text(
        "Mi dispiace, non hai accesso a questo bot. Contatta l'amministratore.",
        reply_markup=ReplyKeyboardRemove()
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        await handle_unauthorized(update)
        return
    user_id = update.effective_user.id
    username = update.effective_user.username
    user = db.get_user(user_id)
    if user:
        await update.message.reply_text(
            f"Bentornato!\nLa tua città attuale è {user.city}\n\n"
            "Usa il pulsante sotto per modificare la città.",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Benvenuto! Per iniziare, usa il pulsante 'Imposta Città' per selezionare la tua città.",
            reply_markup=get_main_keyboard()
        )

async def start_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    await update.message.reply_text(
        "Per favore, invia il nome della città (es. Roma, Milano, Napoli):",
        reply_markup=ReplyKeyboardRemove()
    )
    return WAITING_FOR_CITY

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    city = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username
    db.add_user(user_id, username, city)
    await update.message.reply_text(
        f"Ho impostato la tua città a {city}.\nRiceverai notifiche ogni giorno alle 8:00 (CET) se ci sono partite nella tua città!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def handle_invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Operazione annullata. Usa i pulsanti sotto per riprovare.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def show_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        await handle_unauthorized(update)
        return
    await update.message.reply_text(
        "Usa il pulsante sotto per impostare la tua città.",
        reply_markup=get_main_keyboard()
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Si è verificato un errore. Usa /start per ricominciare.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def run_bot():
    bot_instance = get_bot(config.TELEGRAM_BOT_TOKEN)

    # Add command handlers
    bot_instance.app.add_handler(CommandHandler('start', start))
    bot_instance.app.add_handler(CommandHandler('keyboard', show_keyboard))
    
    # Add conversation handler
    city_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^🏙 Imposta Città$'), start_city_input),
        ],
        states={
            WAITING_FOR_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('keyboard', show_keyboard),
            MessageHandler(filters.ALL, handle_invalid_input)
        ],
    )
    bot_instance.app.add_handler(city_conv_handler)
    
    # Add error handler
    bot_instance.app.add_error_handler(error_handler)
    scheduler = create_scheduler()
    scheduler.start()
    bot_instance.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    # Initialize bot first, before any threads
    bot_instance = get_bot(config.TELEGRAM_BOT_TOKEN)
    logger.info("Bot initialized")
    
    # Start admin interface in a thread
    if config.DEBUG:
        admin_thread = threading.Thread(target=run_admin_interface)
        admin_thread.daemon = True
        admin_thread.start()
        logger.info("Admin interface started in debug mode")
    else:
        admin_thread = threading.Thread(
            target=lambda: os.system(
                f'gunicorn --bind 0.0.0.0:{config.ADMIN_PORT} '
                '--workers 2 --threads 4 --access-logfile - '
                '--error-logfile - wsgi:application'
            )
        )
        admin_thread.daemon = True
        admin_thread.start()
        logger.info("Admin interface started with Gunicorn")
    
    # Start bot polling after admin interface is ready
    run_bot()

if __name__ == '__main__':
    main()
