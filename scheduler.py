from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from storage import Database
from fetcher import MatchFetcher
from config import NOTIFICATION_HOUR, NOTIFICATION_MINUTE

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
        trigger = CronTrigger(
            hour=NOTIFICATION_HOUR,
            minute=NOTIFICATION_MINUTE
        )
        
        self.scheduler.add_job(
            self.check_and_notify_all_users,
            trigger=trigger,
            id='daily_match_check',
            replace_existing=True
        )
        
    def start(self):
        """Start the scheduler."""
        self.setup_daily_job()
        self.scheduler.start()
        
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        
    async def check_and_notify_all_users(self):
        """Check matches for all users and send notifications."""
        users = self.db.get_all_users()
        
        for user in users:
            if user.is_blocked:
                continue
                
            if not self.db.check_access(user.telegram_id):
                continue
                
            message = self.fetcher.check_matches_for_city(user.city)
            
            try:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message
                )
            except Exception as e:
                print(f"Failed to send message to user {user.telegram_id}: {str(e)}")
                
    def get_next_run_time(self) -> datetime:
        """Get the next scheduled run time."""
        job = self.scheduler.get_job('daily_match_check')
        return job.next_run_time if job else None