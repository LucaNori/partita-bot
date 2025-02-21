from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from storage import Database
from fetcher import MatchFetcher
import config

def create_scheduler(bot):
    db = Database()
    fetcher = MatchFetcher()
    scheduler = BackgroundScheduler(timezone="UTC")
    
    def calculate_next_interval():
        """Calculate the next check interval based on current time"""
        current_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        cet_time = current_utc.astimezone(ZoneInfo("Europe/Rome"))
        
        # If we're in the 8-10 AM window, check every 15 minutes
        if 8 <= cet_time.hour < 10:
            return 15 * 60  # 15 minutes in seconds
        
        # Calculate time until 8 AM tomorrow
        tomorrow = cet_time.date() + timedelta(days=1)
        next_run = datetime.combine(tomorrow, datetime.min.time().replace(hour=8))
        next_run = next_run.replace(tzinfo=ZoneInfo("Europe/Rome"))
        
        # Convert to seconds
        seconds_until_next = (next_run - cet_time).total_seconds()
        return max(seconds_until_next, 15 * 60)  # Minimum 15 minutes
    
    def check_and_send_notifications():
        current_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        cet_time = current_utc.astimezone(ZoneInfo("Europe/Rome"))
        print(f"[{current_utc.isoformat()}] Checking notification conditions...")
        
        # Check if we're in the 8-10 AM window
        if not (8 <= cet_time.hour < 10):
            print(f"Outside notification window (current CET time: {cet_time.strftime('%H:%M')})")
            return
        
        # Check if we already ran today
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
                # Check if user already received notification today
                if user.last_notification:
                    last_notif = user.last_notification
                    if last_notif.tzinfo is None:
                        last_notif = last_notif.replace(tzinfo=ZoneInfo("UTC"))
                    if last_notif.date() == current_utc.date():
                        already_notified += 1
                        print(f"Notification already sent today for user {user.telegram_id}")
                        continue
                
                print(f"Checking matches for user {user.telegram_id} in {user.city}...")
                message = fetcher.check_matches_for_city(user.city)
                if message:
                    bot.send_message(chat_id=user.telegram_id, text=message)
                    db.update_last_notification(user.telegram_id)
                    notifications_sent += 1
                    print(f"Notification sent to user {user.telegram_id}")
                else:
                    no_matches += 1
                    print(f"No match found for user {user.telegram_id} in {user.city}")
                    
            except Exception as e:
                print(f"Error processing user {user.telegram_id}: {str(e)}")
        
        if notifications_sent > 0 or no_matches > 0:
            db.update_scheduler_last_run()
            print(f"Job complete. Notifications sent: {notifications_sent}, No matches: {no_matches}, Already notified: {already_notified}")
    
    def dynamic_schedule():
        """Run notifications and schedule next check"""
        check_and_send_notifications()
        
        # Schedule next run based on current time
        next_interval = calculate_next_interval()
        scheduler.add_job(
            dynamic_schedule,
            'date',
            run_date=datetime.utcnow() + timedelta(seconds=next_interval),
            id='morning_notifications',
            replace_existing=True
        )
        print(f"Next check scheduled in {next_interval/3600:.1f} hours")
    
    # Initial schedule
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
