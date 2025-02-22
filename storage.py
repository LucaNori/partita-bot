from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import asyncio
from zoneinfo import ZoneInfo

Base = declarative_base()

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

    def update_last_notification(self, telegram_id: int, is_manual: bool = False):
        user = self.get_user(telegram_id)
        if user:
            now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
            user.last_notification = now
            if is_manual:
                user.last_manual_notification = now
            self.session.commit()

    def can_send_manual_notification(self, telegram_id: int, cooldown_minutes: int = 5) -> bool:
        user = self.get_user(telegram_id)
        if not user or not user.last_manual_notification:
            return True
            
        now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        if user.last_manual_notification.tzinfo is None:
            last_manual = user.last_manual_notification.replace(tzinfo=ZoneInfo("UTC"))
        else:
            last_manual = user.last_manual_notification
            
        time_since_last = now - last_manual
        return time_since_last.total_seconds() >= cooldown_minutes * 60
            
    def format_last_notification(self, telegram_id: int) -> str:
        user = self.get_user(telegram_id)
        if user and user.last_notification:
            rome_time = user.last_notification.astimezone(ZoneInfo('Europe/Rome'))
            return rome_time.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'

    def update_scheduler_last_run(self):
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE scheduler_state SET last_run = :now WHERE id = 1"),
                {"now": datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))}
            )

    def get_scheduler_last_run(self) -> datetime:
        result = self.session.query(SchedulerState).first()
        if result and result.last_run:
            if result.last_run.tzinfo is None:
                return result.last_run.replace(tzinfo=ZoneInfo("UTC"))
            return result.last_run
        return None
        
    async def remove_blocked_users(self, bot) -> dict:
        users = self.get_all_users()
        total = len(users)
        removed = 0
        errors = []
        
        for user in users:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    message = await bot.bot.send_message(
                        chat_id=user.telegram_id,
                        text="test message, please ignore",
                        disable_notification=True
                    )
                    await bot.bot.delete_message(
                        chat_id=user.telegram_id,
                        message_id=message.message_id
                    )
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            except Exception as e:
                error_str = str(e).lower()
                if "forbidden" in error_str and "blocked" in error_str:
                    self.session.delete(user)
                    removed += 1
                else:
                    errors.append(f"User {user.telegram_id}: {str(e)}")
        
        if removed > 0:
            self.session.commit()
            
        return {
            "total_users": total,
            "removed_users": removed,
            "errors": errors
        }
