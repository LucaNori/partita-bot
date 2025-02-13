from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

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

        # Ensure there's at least one access mode record
        if not self.session.query(AccessMode).first():
            default_mode = AccessMode(mode='blocklist')
            self.session.add(default_mode)
            self.session.commit()

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
        """Set the global access mode (whitelist or blocklist)."""
        if mode not in ['whitelist', 'blocklist']:
            raise ValueError("Mode must be either 'whitelist' or 'blocklist'")
        
        access_mode = self.session.query(AccessMode).first()
        access_mode.mode = mode
        self.session.commit()

    def get_access_mode(self) -> str:
        """Get the current access mode."""
        access_mode = self.session.query(AccessMode).first()
        return access_mode.mode if access_mode else 'blocklist'

    def add_to_list(self, mode: str, telegram_id: int):
        """Add a user to whitelist/blocklist"""
        if mode not in ['whitelist', 'blocklist']:
            raise ValueError("Mode must be either 'whitelist' or 'blocklist'")
        
        entry = AccessControl(mode=mode, telegram_id=telegram_id)
        self.session.add(entry)
        self.session.commit()

    def remove_from_list(self, mode: str, telegram_id: int):
        """Remove a user from whitelist/blocklist"""
        self.session.query(AccessControl).filter_by(
            mode=mode, telegram_id=telegram_id
        ).delete()
        self.session.commit()

    def check_access(self, telegram_id: int) -> bool:
        """Check if a user has access based on current mode."""
        mode = self.get_access_mode()
        
        if mode == 'whitelist':
            # In whitelist mode, user must be in whitelist to have access
            return bool(self.session.query(AccessControl).filter_by(
                mode='whitelist', telegram_id=telegram_id
            ).first())
        else:  # blocklist mode
            # In blocklist mode, user must not be in blocklist to have access
            return not bool(self.session.query(AccessControl).filter_by(
                mode='blocklist', telegram_id=telegram_id
            ).first())