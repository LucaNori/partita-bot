import os
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from storage import Database
from fetcher import MatchFetcher
import config

db = Database()
fetcher = MatchFetcher()

def send_morning_notifications():
    """
    This job is scheduled to run every hour at the top of the hour.
    For each user, it converts the current UTC time (made timezone-aware)
    to the user's local time. If the local time is after 07:00 (inclusive)
    and the user hasn't received a notification today, it checks for matches
    in the user's city and sends a notification if one is found.
    """
    current_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    print(f"[{current_utc.isoformat()}] Running notification job...")
    
    users = db.get_all_users()
    for user in users:
        try:
            try:
                user_tz = ZoneInfo(user.timezone)
            except Exception:
                user_tz = ZoneInfo("Europe/Rome")
            
            local_time = current_utc.astimezone(user_tz)
            print(f"User {user.telegram_id}: local time is {local_time.strftime('%H:%M:%S')} ({user_tz.key})")
            
            if local_time.hour >= 7:
                already_sent = False
                if user.last_notification:
                    last_notif = user.last_notification
                    if last_notif.tzinfo is None:
                        last_notif = last_notif.replace(tzinfo=ZoneInfo("UTC"))
                    last_notif_local = last_notif.astimezone(user_tz)
                    if last_notif_local.date() == local_time.date():
                        already_sent = True

                if already_sent:
                    print(f"Notification already sent today for user {user.telegram_id}")
                    continue

                print(f"User {user.telegram_id} is eligible for notification. Checking for matches in {user.city}...")
                message = fetcher.check_matches_for_city(user.city)
                if message:
                    config.BOT.send_message_sync(chat_id=user.telegram_id, text=message)
                    db.update_last_notification(user.telegram_id)
                    print(f"Notification sent to user {user.telegram_id}")
                else:
                    print(f"No match found for user {user.telegram_id} in {user.city}")
        except Exception as e:
            print(f"Error processing user {user.telegram_id}: {str(e)}")

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(send_morning_notifications, "cron", minute=0)
    print("Starting hourly scheduler for morning notifications...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")