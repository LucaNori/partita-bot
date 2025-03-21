from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import config
from storage import Database
from fetcher import MatchFetcher
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import nest_asyncio
from bot_manager import get_bot

nest_asyncio.apply()

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
auth = HTTPBasicAuth()
db = Database()

# Use database to queue messages instead of directly sending them
def send_message_via_db_queue(chat_id: int, text: str):
    """Queue a message in the database to be sent by the bot process"""
    return db.queue_message(telegram_id=chat_id, message=text)
fetcher = MatchFetcher()

users = {
    config.ADMIN_USERNAME: generate_password_hash(config.ADMIN_PASSWORD)
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/')
@auth.login_required
def index():
    access_mode = db.get_access_mode()
    all_users = db.get_all_users()
    return render_template('admin.html', 
                         users=all_users, 
                         access_mode=access_mode,
                         current_mode=access_mode,
                         db=db)

@app.route('/set_mode', methods=['POST'])
@auth.login_required
def set_mode():
    mode = request.form.get('mode', 'blocklist')
    if mode in ['whitelist', 'blocklist']:
        db.set_access_mode(mode)
    return redirect(url_for('index'))

@app.route('/toggle_access/<int:user_id>', methods=['POST'])
@auth.login_required
def toggle_access(user_id):
    mode = db.get_access_mode()
    action = request.form.get('action')
    
    if mode == 'whitelist':
        if action == 'allow':
            db.add_to_list('whitelist', user_id)
        elif action == 'remove':
            db.remove_from_list('whitelist', user_id)
    else:
        if action == 'block':
            db.add_to_list('blocklist', user_id)
        elif action == 'unblock':
            db.remove_from_list('blocklist', user_id)
    
    return redirect(url_for('index'))

@app.route('/cleanup_users', methods=['POST'])
@auth.login_required
def cleanup_users():
    try:
        # Queue a special admin operation in the database
        # The bot will recognize this and perform the cleanup
        db.queue_message(telegram_id=0, message="ADMIN_OPERATION:CLEANUP_USERS")
        flash("User cleanup operation has been queued. Check back later for results.", 'info')
    except Exception as e:
        flash(f'Error during cleanup: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/notify_all', methods=['POST'])
@auth.login_required
def notify_all():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        users = db.get_all_users()
        notifications_sent = 0
        no_matches = 0
        already_notified = 0
        
        current_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        
        for user in users:
            try:
                if user.last_notification:
                    last_notif = user.last_notification
                    if last_notif.tzinfo is None:
                        last_notif = last_notif.replace(tzinfo=ZoneInfo("UTC"))
                    if last_notif.date() == current_utc.date():
                        already_notified += 1
                        continue
                
                message = fetcher.check_matches_for_city(user.city)
                if message:
                    send_message_via_db_queue(
                        chat_id=user.telegram_id,
                        text=message
                    )
                    db.update_last_notification(user.telegram_id)
                    notifications_sent += 1
                else:
                    no_matches += 1
                    
            except Exception as e:
                flash(f'Error processing user {user.telegram_id}: {str(e)}', 'error')
                
        summary = f'Notifications sent: {notifications_sent}, No matches: {no_matches}, Already notified today: {already_notified}'
        flash(summary, 'success' if notifications_sent > 0 else 'info')
            
    except Exception as e:
        flash(f'Error in notify_all: {str(e)}', 'error')
    finally:
        try:
            loop.close()
        except:
            pass
    
    return redirect(url_for('index'))

@app.route('/notify_user/<int:user_id>', methods=['POST'])
@auth.login_required
def notify_user(user_id):
    try:
        user = db.get_user(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('index'))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        message = fetcher.check_matches_for_city(user.city)
        
        if not db.can_send_manual_notification(user_id):
            flash(f'Please wait at least 5 minutes between manual notifications for user {user_id}', 'error')
            return redirect(url_for('index'))

        if message:
            send_message_via_db_queue(
                chat_id=user_id,
                text=message
            )
            db.update_last_notification(user_id, is_manual=True)
            flash(f'Notification sent to user {user_id}', 'success')
        else:
            flash(f'No matches found for user {user_id} in {user.city}. Notification not sent.', 'info')
            
    except Exception as e:
        flash(f'Error sending notification: {str(e)}', 'error')
    finally:
        try:
            loop.close()
        except:
            pass
    
    return redirect(url_for('index'))

@app.route('/test_notification/<int:user_id>', methods=['POST'])
@auth.login_required
def test_notification(user_id):
    try:
        user = db.get_user(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('index'))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not db.can_send_manual_notification(user_id):
            flash(f'Please wait at least 5 minutes between manual notifications for user {user_id}', 'error')
            return redirect(url_for('index'))

        matches = fetcher.get_matches_for_city(user.city)
        
        message = "🎯 Oggi nella tua città ci sono le seguenti partite:\n\n"
        if matches:
            for match in matches:
                message += (f"⚽️ {match['home']} vs {match['away']}\n"
                          f"🕒 {match['time_local']} (CET)\n\n")
        else:
            message += "⚽️ Test Match vs Test Team\n🕒 15:00 (CET)\n\n"

        send_message_via_db_queue(
            chat_id=user_id,
            text=message
        )
        db.update_last_notification(user_id, is_manual=True)
        flash(f'Test notification sent to user {user_id}', 'success')
            
    except Exception as e:
        flash(f'Error sending test notification: {str(e)}', 'error')
    finally:
        try:
            loop.close()
        except:
            pass
    
    return redirect(url_for('index'))

def run_admin_interface():
    app.run(host='0.0.0.0', port=config.ADMIN_PORT)
