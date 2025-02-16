from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, inspect
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
    mode = Column(String, nullable=False)  # 'whitelist' or 'blocklist'
    telegram_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AccessMode(Base):
    __tablename__ = 'access_mode'

    id = Column(Integer, primary_key=True)
    mode = Column(String, nullable=False, default='blocklist')  # 'whitelist' or 'blocklist'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Database:
    def __init__(self):
        db_path = os.path.join('data', 'bot.sqlite3')
        os.makedirs('data', exist_ok=True)
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Run schema upgrade to add last_notification column if it doesn't exist.
        self._upgrade_schema()

        # Ensure there's at least one access mode record.
        if not self.session.query(AccessMode).first():
            default_mode = AccessMode(mode='blocklist')
            self.session.add(default_mode)
            self.session.commit()

    def _upgrade_schema(self):
        """
        Check if the 'last_notification' column exists in the 'users' table.
        If not, add it without affecting existing data.
        """
        inspector = inspect(self.engine)
        columns = [col["name"] for col in inspector.get_columns(User.__tablename__)]
        if "last_notification" not in columns:
            with self.engine.connect() as conn:
                conn.execute("ALTER TABLE users ADD COLUMN last_notification DATETIME")

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
            user.last_notification = func.now()
            self.session.commit()
            
    def format_last_notification(self, telegram_id: int) -> str:
        user = self.get_user(telegram_id)
        if user and user.last_notification:
            rome_time = user.last_notification.astimezone(ZoneInfo('Europe/Rome'))
            return rome_time.strftime('%Y-%m-%d %H:%M:%S')
        return 'Never'