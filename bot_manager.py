from typing import Optional
from custom_bot import Bot

_bot_instance: Optional[Bot] = None

def get_bot(token: str) -> Bot:
    """Get or create the bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token)
    return _bot_instance
