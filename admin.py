from flask import Flask, render_template_string, request, redirect, url_for, Response
from functools import wraps
import config
from storage import Database

app = Flask(__name__)
db = Database()

# HTML template for the admin interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bot Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .blocked { background-color: #ffe6e6; }
        .button { 
            padding: 5px 10px;
            margin: 2px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        .block { background-color: #ff4444; color: white; }
        .unblock { background-color: #44ff44; color: black; }
        .mode-switch {
            margin: 20px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <h1>Bot Admin Panel</h1>
    
    <div class="mode-switch">
        <h3>Access Control Mode</h3>
        <form method="post" action="{{ url_for('set_mode') }}">
            <select name="mode">
                <option value="blocklist" {% if current_mode == 'blocklist' %}selected{% endif %}>Blocklist Mode</option>
                <option value="whitelist" {% if current_mode == 'whitelist' %}selected{% endif %}>Whitelist Mode</option>
            </select>
            <button type="submit" class="button">Set Mode</button>
        </form>
    </div>

    <h2>Users</h2>
    <table>
        <tr>
            <th>Telegram ID</th>
            <th>Username</th>
            <th>City</th>
            <th>Created At</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
        {% for user in users %}
        <tr {% if user.is_blocked %}class="blocked"{% endif %}>
            <td>{{ user.telegram_id }}</td>
            <td>{{ user.username or 'N/A' }}</td>
            <td>{{ user.city }}</td>
            <td>{{ user.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
            <td>{{ 'Blocked' if user.is_blocked else 'Active' }}</td>
            <td>
                {% if user.is_blocked %}
                <form method="post" action="{{ url_for('unblock_user', telegram_id=user.telegram_id) }}" style="display: inline;">
                    <button type="submit" class="button unblock">Unblock</button>
                </form>
                {% else %}
                <form method="post" action="{{ url_for('block_user', telegram_id=user.telegram_id) }}" style="display: inline;">
                    <button type="submit" class="button block">Block</button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
'''

def check_auth(username, password):
    """Check if the provided credentials are valid."""
    return username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD

def authenticate():
    """Send a 401 response that enables basic auth."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    users = db.get_all_users()
    # TODO: Implement current_mode detection from AccessControl table
    current_mode = 'blocklist'  # Default mode
    return render_template_string(HTML_TEMPLATE, users=users, current_mode=current_mode)

@app.route('/block/<int:telegram_id>', methods=['POST'])
@requires_auth
def block_user(telegram_id):
    db.block_user(telegram_id)
    return redirect(url_for('index'))

@app.route('/unblock/<int:telegram_id>', methods=['POST'])
@requires_auth
def unblock_user(telegram_id):
    db.unblock_user(telegram_id)
    return redirect(url_for('index'))

@app.route('/set_mode', methods=['POST'])
@requires_auth
def set_mode():
    mode = request.form.get('mode')
    if mode in ['whitelist', 'blocklist']:
        # TODO: Implement mode switching in database
        pass
    return redirect(url_for('index'))

def run_admin_interface():
    """Run the Flask admin interface."""
    app.run(
        host='0.0.0.0',
        port=config.ADMIN_PORT,
        debug=False
    )