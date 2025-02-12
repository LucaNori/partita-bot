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
                         current_mode=access_mode)

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

# Templates directory content
TEMPLATES = {
    'admin.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Bot Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { margin-bottom: 20px; }
        .mode-selector { margin-bottom: 20px; padding: 10px; background: #f5f5f5; }
        .user-list { border-collapse: collapse; width: 100%; }
        .user-list td, .user-list th { border: 1px solid #ddd; padding: 8px; }
        .user-list tr:nth-child(even) { background-color: #f9f9f9; }
        .user-list th { background-color: #4CAF50; color: white; }
        .button { 
            padding: 6px 12px;
            margin: 2px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .block { background-color: #f44336; color: white; }
        .allow { background-color: #4CAF50; color: white; }
        .unblock, .remove { background-color: #2196F3; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bot Admin Panel</h1>
        </div>
        
        <div class="mode-selector">
            <h3>Access Control Mode</h3>
            <form method="POST" action="{{ url_for('set_mode') }}">
                <label>
                    <input type="radio" name="mode" value="blocklist" 
                           {% if current_mode == 'blocklist' %}checked{% endif %}> Blocklist Mode
                </label>
                <label>
                    <input type="radio" name="mode" value="whitelist" 
                           {% if current_mode == 'whitelist' %}checked{% endif %}> Whitelist Mode
                </label>
                <button type="submit" class="button">Update Mode</button>
            </form>
        </div>

        <h3>Users</h3>
        <table class="user-list">
            <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>City</th>
                <th>Actions</th>
            </tr>
            {% for user in users %}
            <tr>
                <td>{{ user.telegram_id }}</td>
                <td>{{ user.username or 'N/A' }}</td>
                <td>{{ user.city }}</td>
                <td>
                    <form method="POST" action="{{ url_for('toggle_access', user_id=user.telegram_id) }}" style="display: inline;">
                        {% if current_mode == 'whitelist' %}
                            {% if not db.check_access(user.telegram_id) %}
                                <input type="hidden" name="action" value="allow">
                                <button type="submit" class="button allow">Allow</button>
                            {% else %}
                                <input type="hidden" name="action" value="remove">
                                <button type="submit" class="button remove">Remove</button>
                            {% endif %}
                        {% else %}
                            {% if db.check_access(user.telegram_id) %}
                                <input type="hidden" name="action" value="block">
                                <button type="submit" class="button block">Block</button>
                            {% else %}
                                <input type="hidden" name="action" value="unblock">
                                <button type="submit" class="button unblock">Unblock</button>
                            {% endif %}
                        {% endif %}
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''
}