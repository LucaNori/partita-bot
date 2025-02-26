# Partita Bot

Partita Bot is a Telegram bot that notifies users about daily football matches. Born because i was tired of finding myself in traffic jams in my city, and shared for every frustrated user with my same problem.
To use the bot, the end user can configure their city with a simple telegram chat. The bot fetches match data daily via an integrated scheduler and sends notifications within the configured time window if a match is scheduled. An admin panel provides web-based controls for managing users and the bot access mode (blocklist/whitelist).

## Features

- **Daily Notifications:** The bot checks for football matches in a user's configured city and sends a notification every morning during the configured notification window if a match is scheduled.
- **Message Queue System:** Reliable message delivery through a database-backed queue to prevent Telegram API conflicts.
- **User Configuration:** New users are prompted to set their city. Existing users can update their settings.
- **Admin Panel:** A simple Flask-based admin interface for managing mode settings and users (allow, block, unblock, or remove). Includes access control and flash notifications.
- **Container Separation:** Bot and admin services can run in separate containers to improve stability and prevent API conflicts.
- **Scheduler:** APScheduler is used for periodic job execution. The scheduler fetches match data on a set schedule.
- **Docker Ready:** The project is containerized using Docker. There are separate configurations for production and local development.

## Project Structure

```
├── .env.example             # Sample environment variables file
├── .gitignore
├── Dockerfile               # Docker container build instructions
├── docker-compose.yml       # Production deployment Docker Compose file
├── docker-compose.local.yml # Local deployment Docker Compose file for testing changes
├── admin.py                 # Flask-based admin panel
├── bot.py                   # Main Telegram bot code handling commands and messaging
├── bot_manager.py           # Singleton pattern for managing bot instance
├── config.py                # Configuration variables and settings
├── CHANGELOG.md
├── DEVELOPER_GUIDE.md       # Developer instructions and best practices
├── custom_bot.py            # Custom Bot class with sync message support
├── fetcher.py               # Module for fetching match data (e.g., from an API or local source)
├── LICENSE
├── README.md                # This documentation file
├── requirements.txt         # Python dependencies
├── run_bot.py               # Standalone entry point for the bot service
├── scheduler.py             # Scheduler setup with APScheduler to schedule notification jobs
├── storage.py               # Database module for user data and message queue (using SQLAlchemy)
├── teams.yml                # Teams configuration file
├── wsgi.py                  # WSGI application entry point for the admin interface
├── static/                  
│   └── favicon.ico          # Favicon for the admin panel
└── templates/
    └── admin.html           # Admin panel HTML template with favicon link
```

## Setup and Configuration

1. **Environment Variables:**  
   Copy `.env.example` to `.env` and update the necessary variables. Common settings include:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_PORT`: Port for the admin interface
   - `ADMIN_USERNAME`/`ADMIN_PASSWORD`: Admin panel credentials
   - `NOTIFICATION_START_HOUR`/`NOTIFICATION_END_HOUR`: Notification time window
   - `SERVICE_TYPE`: Can be "bot", "admin", or empty to run both

2. **Dependencies:**  
   All dependencies are listed in `requirements.txt`. They include:
   - python-telegram-bot (v20.7)
   - Flask and Flask-HTTPAuth
   - SQLAlchemy
   - APScheduler
   - nest_asyncio (for handling nested event loops)
   - Other libraries such as pytz, requests, PyYAML, and python-dotenv

3. **Database:**  
   The `storage.py` module handles database operations including:
   - User management
   - Message queue for reliable notifications
   - Scheduler state tracking

## Running the Bot

### Via Docker (Production)

1. **Build and run:**
   ```bash
   docker compose up -d --build
   ```
   This uses the default `docker-compose.yml` which supports separated services.

2. **Logs:**
   Monitor logs with:
   ```bash
   docker compose logs -f
   ```

### Separate Services Deployment

For improved stability, you can run the bot and admin panel as separate services:

1. **Run bot service only:**
   ```bash
   SERVICE_TYPE=bot docker compose up -d
   ```

2. **Run admin panel only:**
   ```bash
   SERVICE_TYPE=admin docker compose up -d
   ```

### Local Development

For local testing with your latest changes without pushing to GitHub, use `docker-compose.local.yml`:

1. **Build and run locally:**
   ```bash
   docker compose -f docker-compose.local.yml up -d --build
   ```

2. **Access Admin Panel:**
   Open your browser and navigate to `http://localhost:5000` (or the port specified in your `.env`).

3. **Logs:**
   Check real-time logs:
   ```bash
   docker compose -f docker-compose.local.yml logs -f
   ```

## Contributing

Contributions are welcome. Please refer to `DEVELOPER_GUIDE.md` for guidelines on code style, testing, and Git workflow.

## License

This project is licensed under the terms found in the [LICENSE](LICENSE) file.