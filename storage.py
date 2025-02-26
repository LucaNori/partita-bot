from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import asyncio
import logging
import json
from zoneinfo import ZoneInfo

Base = declarative_base()

# Table to store pending messages for the bot to send
class MessageQueue(Base):
    __tablename__ = 'message_queue'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    city = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    last_notification = Column(DateTime, nullable=True)
    last_manual_notification = Column(DateTime, nullable=True)

class AccessControl(Base):
    __tablename__ = 'access_control'

    id = Column(Integer, primary_key=True)
    mode = Column(String, nullable=False)
    telegram_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AccessMode(Base):
    __tablename__ = 'access_mode'

    id = Column(Integer, primary_key=True)
    mode = Column(String, nullable=False, default='blocklist')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SchedulerState(Base):
    __tablename__ = 'scheduler_state'

    id = Column(Integer, primary_key=True)
    last_run = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Database:
    def __init__(self):
        db_path = os.path.join('data', 'bot.sqlite3')
        os.makedirs('data', exist_ok=True)
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self._upgrade_schema()

        if not self.session.query(AccessMode).first():
            default_mode = AccessMode(mode='blocklist')
            self.session.add(default_mode)
            self.session.commit()

    def _upgrade_schema(self):
        inspector = inspect(self.engine)
        
        user_columns = [col["name"] for col in inspector.get_columns(User.__tablename__)]
        if "last_notification" not in user_columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_notification DATETIME"))
        if "last_manual_notification" not in user_columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_manual_notification DATETIME"))
        
        if not inspector.has_table('scheduler_state'):
            SchedulerState.__table__.create(self.engine)
            with self.engine.begin() as conn:
                conn.execute(text("INSERT INTO scheduler_state (id) VALUES (1)"))

    def add_user(self, telegram_id: int, username: str, city: str) -> User:
        user = self.session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.username = username
            user.city = city
        else:
            user = User(telegram_id=telegram_id, username=username, city=city)
            self.session.add(user)
        self.session.commit()
        return user

    def get_user(self, telegram_id: int) -> User:
        return self.session.query(User).filter_by(telegram_id=telegram_id).first()

    def get_all_users(self):
        return self.session.query(User).all()

    def block_user(self, telegram_id: int) -> bool:
        user = self.get_user(telegram_id)
        if user:
            user.is_blocked = True
            self.session.commit()
            return True
        return False

    def unblock_user(self, telegram_id: int) -> bool:
        user = self.get_user(telegram_id)
        if user:
            user.is_blocked = False
            self.session.commit()
            return True
        return False

    def set_access_mode(self, mode: str):
        if mode not in ['whitelist', 'blocklist']:
            raise ValueError("Mode must be either 'whitelist' or 'blocklist'")
        access_mode = self.session.query(AccessMode).first()
        access_mode.mode = mode
        self.session.commit()

    def get_access_mode(self) -> str:
        access_mode = self.session.query(AccessMode).first()
        return access_mode.mode if access_mode else 'blocklist'

    def add_to_list(self, mode: str, telegram_id: int):
        if mode not in ['whitelist', 'blocklist']:
            raise ValueError("Mode must be either 'whitelist' or 'blocklist'")
        entry = AccessControl(mode=mode, telegram_id=telegram_id)
        self.session.add(entry)
        self.session.commit()

    def remove_from_list(self, mode: str, telegram_id: int):
        self.session.query(AccessControl).filter_by(
            mode=mode, telegram_id=telegram_id
        ).delete()
        self.session.commit()

    def check_access(self, telegram_id: int) -> bool:
        mode = self.get_access_mode()
        if mode == 'whitelist':
            return bool(self.session.query(AccessControl).filter_by(
                mode='whitelist', telegram_id=telegram_id
            ).first())
        else:
            return not bool(self.session.query(AccessControl).filter_by(
                mode='blocklist', telegram_id=telegram_id
            ).first())

    def _get_utc_now(self) -> datetime:
        """Get current UTC time with timezone info"""
        return datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        
    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone aware (UTC)"""
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=ZoneInfo("UTC"))

    def update_last_notification(self, telegram_id: int, is_manual: bool = False):
        """Update the last notification timestamp for a user"""
        user = self.get_user(telegram_id)
        if user:
            now = self._get_utc_now()
            user.last_notification = now
            if is_manual:
                user.last_manual_notification = now
            self.session.commit()

    def can_send_manual_notification(self, telegram_id: int, cooldown_minutes: int = 5) -> bool:
        """Check if a manual notification can be sent based on cooldown time"""
        user = self.get_user(telegram_id)
        if not user or not user.last_manual_notification:
            return True
            
        now = self._get_utc_now()
        last_manual = self._ensure_timezone_aware(user.last_manual_notification)
        time_since_last = now - last_manual
        
        return time_since_last.total_seconds() >= cooldown_minutes * 60
            
    def format_last_notification(self, telegram_id: int) -> str:
        """Format the last notification time for display"""
        user = self.get_user(telegram_id)
        if user and user.last_notification:
            tz_aware = self._ensure_timezone_aware(user.last_notification)
            rome_time = tz_aware.astimezone(ZoneInfo('Europe/Rome'))
            return rome_time.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'

    def update_scheduler_last_run(self):
        """Update the last run time of the scheduler"""
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE scheduler_state SET last_run = :now WHERE id = 1"),
                {"now": self._get_utc_now()}
            )

    def get_scheduler_last_run(self) -> datetime:
        """Get the last time the scheduler ran"""
        result = self.session.query(SchedulerState).first()
        if result and result.last_run:
            return self._ensure_timezone_aware(result.last_run)
        return None
        
    def queue_message(self, telegram_id: int, message: str) -> bool:
        """Queue a message to be sent by the bot process"""
        try:
            queue_item = MessageQueue(
                telegram_id=telegram_id,
                message=message,
                created_at=self._get_utc_now()
            )
            self.session.add(queue_item)
            self.session.commit()
            logger = logging.getLogger(__name__)
            logger.info(f"Message queued for user {telegram_id}")
            return True
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error queueing message: {str(e)}")
            return False
            
    def get_pending_messages(self, limit: int = 10) -> list:
        """Get pending messages to be sent"""
        return self.session.query(MessageQueue)\
            .filter(MessageQueue.sent == False)\
            .order_by(MessageQueue.created_at)\
            .limit(limit)\
            .all()
            
    def mark_message_sent(self, message_id: int) -> bool:
        """Mark a message as sent"""
        try:
            message = self.session.query(MessageQueue).get(message_id)
            if message:
                message.sent = True
                message.sent_at = self._get_utc_now()
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error marking message as sent: {str(e)}")
            return False
        
    async def remove_blocked_users(self, bot) -> dict:
        users = self.get_all_users()
        total = len(users)
        removed = 0
        errors = []
        logger = logging.getLogger(__name__)
        
        for user in users:
            user_id = user.telegram_id
            logger.debug(f"Checking if user {user_id} has blocked the bot")
            
            try:
                message = await bot.bot.send_message(
                    chat_id=user_id,
                    text="test message, please ignore",
                    disable_notification=True
                )
                
                # Message sent successfully, user has not blocked the bot
                await bot.bot.delete_message(
                    chat_id=user_id,
                    message_id=message.message_id
                )
                logger.debug(f"User {user_id} has not blocked the bot")
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if user has blocked the bot
                if "forbidden" in error_str and "blocked" in error_str:
                    logger.info(f"Removing user {user_id} who blocked the bot")
                    self.session.delete(user)
                    removed += 1
                else:
                    logger.warning(f"Error checking user {user_id}: {str(e)}")
                    errors.append(f"User {user_id}: {str(e)}")
        
        # Commit changes if any users were removed
        if removed > 0:
            self.session.commit()
            logger.info(f"Removed {removed} users who blocked the bot")
            
        return {
            "total_users": total,
            "removed_users": removed,
            "errors": errors
        }
