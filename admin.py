from flask import Flask, render_template, request, redirect, url_for, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import config
from storage import Database

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
auth = HTTPBasicAuth()
db = Database()

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
    else:  # blocklist mode
        if action == 'block':
            db.add_to_list('blocklist', user_id)
        elif action == 'unblock':
            db.remove_from_list('blocklist', user_id)
    
    return redirect(url_for('index'))

def run_admin_interface():
    """Run the admin interface."""
    app.run(host='0.0.0.0', port=config.ADMIN_PORT)