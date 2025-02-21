from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from zoneinfo import ZoneInfo

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    city = Column(String, nullable=False)
    timezone = Column(String, default='Europe/Rome')
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    last_notification = Column(DateTime, nullable=True)

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
        
        # Check and add last_notification column to users table
        user_columns = [col["name"] for col in inspector.get_columns(User.__tablename__)]
        if "last_notification" not in user_columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_notification DATETIME"))
        
        # Create scheduler_state table if it doesn't exist
        if not inspector.has_table('scheduler_state'):
            SchedulerState.__table__.create(self.engine)
            with self.engine.begin() as conn:
                conn.execute(text("INSERT INTO scheduler_state (id) VALUES (1)"))

    def add_user(self, telegram_id: int, username: str, city: str, timezone: str = 'Europe/Rome') -> User:
        user = self.session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.username = username
            user.city = city
            user.timezone = timezone
        else:
            user = User(telegram_id=telegram_id, username=username, city=city, timezone=timezone)
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

    def update_last_notification(self, telegram_id: int):
        user = self.get_user(telegram_id)
        if user:
            user.last_notification = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
            self.session.commit()
            
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
