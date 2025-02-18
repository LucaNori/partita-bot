import nest_asyncio
nest_asyncio.apply()

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
from scheduler import create_scheduler
from admin import run_admin_interface
import config
import threading

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

WAITING_FOR_CITY = 1
WAITING_FOR_TIMEZONE = 2

class Bot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.bot = self.app.bot
        self._loop = None

    def send_message_sync(self, chat_id: int, text: str):
        async def _send():
            await self.bot.send_message(chat_id=chat_id, text=text)
        
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(_send())
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop.run_until_complete(_send())
            else:
                raise

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ['🏙 Imposta Città', '🕒 Imposta Fuso Orario']
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
            f"Bentornato!\nLa tua città attuale è {user.city}\nIl tuo fuso orario è {user.timezone}\n\n"
            "Usa i pulsanti sotto per modificare le impostazioni.",
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
    user = db.get_user(user_id)
    timezone = user.timezone if user else 'Europe/Rome'
    db.add_user(user_id, username, city, timezone)
    await update.message.reply_text(
        f"Ho impostato la tua città a {city}.\nRiceverai notifiche ogni giorno alle 7:00 del tuo fuso orario se ci sono partite nella tua città!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def start_timezone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
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
    if not await check_access(update):
        await handle_unauthorized(update)
        return ConversationHandler.END
    timezone_str = update.message.text
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
        username = update.effective_user.username
        city = "da impostare"
        db.add_user(user_id, username, city, timezone_str)
    await update.message.reply_text(
        f"Ho impostato il tuo fuso orario a {timezone_str}.\nRiceverai notifiche alle 7:00 del tuo fuso orario!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def handle_invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Operazione annullata. Usa i pulsanti sotto per riprovare.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

def run_bot():
    config.BOT = Bot(config.TELEGRAM_BOT_TOKEN)
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
    timezone_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^🕒 Imposta Fuso Orario$'), start_timezone_input),
        ],
        states={
            WAITING_FOR_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_timezone)],
        },
        fallbacks=[MessageHandler(filters.ALL, handle_invalid_input)],
    )
    config.BOT.app.add_handler(city_conv_handler)
    config.BOT.app.add_handler(timezone_conv_handler)
    scheduler = create_scheduler(config.BOT.bot)
    scheduler.start()
    config.BOT.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    admin_thread = threading.Thread(target=run_admin_interface)
    admin_thread.daemon = True
    admin_thread.start()
    run_bot()

if __name__ == '__main__':
    main()