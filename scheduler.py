from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from storage import Database
from fetcher import MatchFetcher
import pytz

class MatchScheduler:
    def __init__(self, bot):
        """
        Initialize the scheduler with a bot instance.
        
        Args:
            bot: The telegram bot instance used to send notifications
        """
        self.bot = bot
        self.db = Database()
        self.fetcher = MatchFetcher()
        self.scheduler = BackgroundScheduler()
        
    def setup_daily_job(self):
        """Setup the daily job to check matches and notify users."""
        # Get all users
        users = self.db.get_all_users()
        
        # Create a job for each user's timezone
        for user in users:
            if user.is_blocked:
                continue
                
            if not self.db.check_access(user.telegram_id):
                continue

            try:
                # Create a trigger for 7 AM in the user's timezone
                trigger = CronTrigger(
                    hour=7,
                    minute=0,
                    timezone=pytz.timezone(user.timezone)
                )
                
                # Add job for this user
                self.scheduler.add_job(
                    self.notify_user,
                    trigger=trigger,
                    args=[user.telegram_id, user.city],
                    id=f'notify_user_{user.telegram_id}',
                    replace_existing=True
                )
            except Exception as e:
                print(f"Failed to schedule job for user {user.telegram_id}: {str(e)}")
        
    def start(self):
        """Start the scheduler."""
        self.setup_daily_job()
        self.scheduler.start()
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        
    async def notify_user(self, telegram_id: int, city: str):
        """
        Send match notification to a specific user.
        
        Args:
            telegram_id (int): The user's Telegram ID
            city (str): The user's city
        """
        # Verify user still has access
        if not self.db.check_access(telegram_id):
            return
            
        # Get user and verify not blocked
        user = self.db.get_user(telegram_id)
        if not user or user.is_blocked:
            return
            
        message = self.fetcher.check_matches_for_city(city)
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message
            )
        except Exception as e:
            print(f"Failed to send message to user {telegram_id}: {str(e)}")
                
    def get_next_run_time(self, telegram_id: int) -> datetime:
        """Get the next scheduled run time for a specific user."""
        job = self.scheduler.get_job(f'notify_user_{telegram_id}')
        return job.next_run_time if job else None