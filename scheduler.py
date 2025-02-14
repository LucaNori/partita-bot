from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from storage import Database
from fetcher import MatchFetcher
import pytz
import asyncio

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
                    self._notify_user_sync,  # Use sync wrapper
                    trigger=trigger,
                    args=[user.telegram_id, user.city],
                    id=f'notify_user_{user.telegram_id}',
                    replace_existing=True
                )
                print(f"Scheduled notification for user {user.telegram_id} at 7 AM {user.timezone}")
            except Exception as e:
                print(f"Failed to schedule job for user {user.telegram_id}: {str(e)}")
        
    def start(self):
        """Start the scheduler."""
        self.setup_daily_job()
        self.scheduler.start()
        print("Scheduler started")
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        
    def _notify_user_sync(self, telegram_id: int, city: str):
        """Synchronous wrapper for notify_user."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.notify_user(telegram_id, city))
        
    async def notify_user(self, telegram_id: int, city: str):
        """
        Send match notification to a specific user.
        
        Args:
            telegram_id (int): The user's Telegram ID
            city (str): The user's city
        """
        print(f"Running notification check for user {telegram_id} in {city}")
        
        # Verify user still has access
        if not self.db.check_access(telegram_id):
            print(f"User {telegram_id} does not have access")
            return
            
        # Get user and verify not blocked
        user = self.db.get_user(telegram_id)
        if not user or user.is_blocked:
            print(f"User {telegram_id} is blocked or not found")
            return
            
        message = self.fetcher.check_matches_for_city(city)
        
        # Only send notification if there are matches
        if message:
            try:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=message
                )
                print(f"Sent match notification to user {telegram_id}")
            except Exception as e:
                print(f"Failed to send message to user {telegram_id}: {str(e)}")
        else:
            print(f"No matches found for user {telegram_id} in {city}")
                
    def get_next_run_time(self, telegram_id: int) -> datetime:
        """Get the next scheduled run time for a specific user."""
        job = self.scheduler.get_job(f'notify_user_{telegram_id}')
        if job:
            next_run = job.next_run_time
            print(f"Next notification for user {telegram_id}: {next_run}")
            return next_run
        return None