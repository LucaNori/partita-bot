import nest_asyncio
nest_asyncio.apply()

import asyncio
import logging
from telegram.ext import Application

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.bot = self.app.bot
        self._loop = None

    def send_message_sync(self, chat_id: int, text: str):
        async def _send():
            try:
                await self.bot.send_message(chat_id=chat_id, text=text)
                return True, None
            except Exception as e:
                logger.error(f"Error sending message to {chat_id}: {str(e)}")
                return False, str(e)
        
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        try:
            success, error = self._loop.run_until_complete(_send())
            if not success:
                raise Exception(error)
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                success, error = self._loop.run_until_complete(_send())
                if not success:
                    raise Exception(error)
            else:
                raise
