from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from storage import Database
from fetcher import MatchFetcher
from bot_manager import get_bot
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import config
import logging

logger = logging.getLogger(__name__)

scheduler_logger = logging.getLogger('apscheduler')
scheduler_logger.setLevel(logging.DEBUG if config.DEBUG else logging.WARNING)

TIMEZONE = config.TIMEZONE_INFO

def create_scheduler():
    db = Database()
    fetcher = MatchFetcher()
    bot = get_bot(config.TELEGRAM_BOT_TOKEN)
    scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            'misfire_grace_time': 15*60,
            'coalesce': True  # Combine multiple missed runs into a single run
        }
    )
    
    def calculate_next_interval():
        """Calculate the next check interval based on current time"""
        current_utc = datetime.utcnow().replace(tzinfo=TIMEZONE)
        local_time = current_utc.astimezone(TIMEZONE)

        if config.NOTIFICATION_START_HOUR <= local_time.hour < config.NOTIFICATION_END_HOUR:
            return 15 * 60

        tomorrow = local_time.date() + timedelta(days=1)
        next_run = datetime.combine(tomorrow, datetime.min.time().replace(hour=config.NOTIFICATION_START_HOUR))
        next_run = next_run.replace(tzinfo=TIMEZONE)

        seconds_until_next = (next_run - local_time).total_seconds()
        return max(seconds_until_next, 15 * 60)  # Minimum 15 minutes
    
    def check_and_send_notifications():
        current_utc = datetime.utcnow().replace(tzinfo=TIMEZONE)
        local_time = current_utc.astimezone(TIMEZONE)
        print(f"[{current_utc.isoformat()}] Checking notification conditions...")
        
        if not (config.NOTIFICATION_START_HOUR <= local_time.hour < config.NOTIFICATION_END_HOUR):
            print(f"Outside notification window (current time: {local_time.strftime('%H:%M')} {TIMEZONE})")
            return

        last_run = db.get_scheduler_last_run()
        if last_run and last_run.date() == current_utc.date():
            print("Notifications already sent today")
            return
            
        users = db.get_all_users()
        notifications_sent = 0
        no_matches = 0
        already_notified = 0
        
        for user in users:
            try:
                if user.last_notification:
                    last_notif = user.last_notification
                    if last_notif.tzinfo is None:
                        last_notif = last_notif.replace(tzinfo=TIMEZONE)
                    if last_notif.date() == local_time.date():
                        already_notified += 1
                        print(f"Notification already sent today for user {user.telegram_id}")
                        continue
                
                print(f"Checking matches for user {user.telegram_id} in {user.city}...")
                try:
                    message = fetcher.check_matches_for_city(user.city)
                    if message:
                        try:
                            # Queue the message instead of sending it directly
                            if db.queue_message(
                                telegram_id=user.telegram_id,
                                message=message
                            ):
                                db.update_last_notification(user.telegram_id)
                                notifications_sent += 1
                                print(f"Notification queued for user {user.telegram_id}")
                            else:
                                print(f"Failed to queue notification for user {user.telegram_id}")
                        except Exception as send_error:
                            print(f"Error queueing message for user {user.telegram_id}: {str(send_error)}")
                    else:
                        no_matches += 1
                        print(f"No match found for user {user.telegram_id} in {user.city}")
                except Exception as fetch_error:
                    print(f"Error fetching matches for user {user.telegram_id}: {str(fetch_error)}")
                    
            except Exception as e:
                print(f"Error processing user {user.telegram_id}: {str(e)}")
                logger.error(f"Scheduler error for user {user.telegram_id}: {str(e)}", exc_info=True)
        
        if notifications_sent > 0 or no_matches > 0:
            db.update_scheduler_last_run()
            print(f"Job complete. Notifications sent: {notifications_sent}, No matches: {no_matches}, Already notified: {already_notified}")
    
    def dynamic_schedule():
        """Run notifications and schedule next check"""
        check_and_send_notifications()

        next_interval = calculate_next_interval()
        scheduler.add_job(
            dynamic_schedule,
            'date',
            run_date=datetime.utcnow() + timedelta(seconds=next_interval),
            id='morning_notifications',
            replace_existing=True
        )
        print(f"Next check scheduled in {next_interval/3600:.1f} hours")

    scheduler.add_job(dynamic_schedule, 'date', run_date=datetime.utcnow(), id='morning_notifications')
    
    class MatchScheduler:
        def start(self):
            print("Starting hourly scheduler for morning notifications...")
            scheduler.start()
        def stop(self):
            print("Stopping scheduler...")
            scheduler.shutdown()
            print("Scheduler stopped.")
    
    return MatchScheduler()

print("scheduler.py loaded: exporting create_scheduler")
