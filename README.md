# Partita Bot

Partita Bot is a Telegram bot that notifies users about daily football matches. Born because i was tired of finding myself in traffic jams in my city, and shared for every frustrated user with my same problem.
To use the bot, the end user can configure their city with a simple telegram chat. The bot fetches match data daily via an integrated scheduler and sends notifications at 7:00 AM local time if a match is scheduled in that day. An admin panel provides web-based controls for managing users and the bot access mode (blocklist/whitelist).

## Features

- **Daily Notifications:** The bot checks for football matches in a user's configured city and sends a notification every morning at 7:00 AM local time if a match is scheduled.
- **User Configuration:** New users are prompted to set their city and time zone. Existing users can update their settings.
- **Admin Panel:** A simple Flask-based admin interface for managing mode settings and users (allow, block, unblock, or remove). Includes access control and flash notifications.
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
├── config.py                # Configuration variables and global bot instance
├── CHANGELOG.md
├── DEVELOPER_GUIDE.md       # Developer instructions and best practices
├── fetcher.py               # Module for fetching match data (e.g., from an API or local source)
├── LICENSE
├── README.md                # This documentation file
├── requirements.txt         # Python dependencies
├── scheduler.py             # Scheduler setup with APScheduler to schedule notification jobs
├── storage.py               # Database module for user data and notifications (using SQLAlchemy, etc.)
├── teams.yml                # (Optional) Teams configuration file
├── static/                  
│   └── favicon.ico          # Favicon for the admin panel
└── templates/
    └── admin.html         # Admin panel HTML template with favicon link
```

## Setup and Configuration

1. **Environment Variables:**  
   Copy `.env.example` to `.env` and update the necessary variables. Common settings include the Telegram bot token, admin port, and database connection details.

2. **Dependencies:**  
   All dependencies are listed in `requirements.txt`. They include:
   - python-telegram-bot (v20.7)
   - Flask and Flask-HTTPAuth
   - SQLAlchemy
   - APScheduler
   - nest_asyncio (for handling nested event loops)
   - Other libraries such as pytz, requests, PyYAML, and python-dotenv

3. **Database:**  
   The `storage.py` module handles database operations. Make sure your database is configured per your environment variables.

## Running the Bot

### Via Docker (Production)

1. **Build and run:**
   ```bash
   docker compose up -d --build
   ```
   This uses the default `docker-compose.yml` which might deploy the container from a prebuilt image if configured.

2. **Logs:**
   Monitor logs with:
   ```bash
   docker compose logs -f
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