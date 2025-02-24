# Developer Guide

## Project Structure

```
partita-bot/
├── admin.py           # Flask admin interface with auth and user management
├── bot.py            # Main bot implementation with async handlers
├── config.py         # Configuration and environment variables
├── fetcher.py        # Match fetching and filtering logic
├── scheduler.py      # Notification scheduling with APScheduler
├── storage.py        # SQLAlchemy models and database operations
├── teams.yml         # Team to city mapping configuration
├── docker-compose.yml       # Production deployment configuration
├── docker-compose.local.yml # Local development configuration
├── static/                  # Static assets for admin interface
│   └── favicon.ico         # Admin panel favicon
├── templates/              # HTML templates
│   └── admin.html         # Admin interface template
└── requirements.txt        # Project dependencies
```

## Core Components

### Database (storage.py)
- SQLite database with SQLAlchemy ORM
- Tables: users, access_control, access_mode, and scheduler_state
- Handles user management and access control
- Tracks both automated and manual notification timestamps
- Supports notification rate limiting
- Implements timezone-aware timestamps
- Supports both whitelist and blocklist modes

### Match Fetcher (fetcher.py)
- Interfaces with football-data.org API
- Caches responses to minimize API calls
- Maps teams to cities using teams.yml
- Auto-cleans old cache files
- Case-insensitive city matching

### Scheduler (scheduler.py)
- Uses APScheduler for reliable job execution
- Runs hourly checks for each user
- Sends notifications at 7 AM CET
- Prevents duplicate notifications same day
- Tracks last run time in database

### Bot (bot.py)
- Uses python-telegram-bot v20.7
- Implements conversation flows for settings
- Handles async operations with nest_asyncio
- Manages user registration and preferences
- Integrates scheduler for notifications
- Proper event loop management

### Admin Interface (admin.py)
- Flask-based web interface
- User management with access control
- Manual notification triggers with rate limiting
- Test notification support
- User activity monitoring
- Custom favicon and styling
- Proper error handling and feedback

## Development Setup

### Requirements
- Python 3.10+
- Docker and Docker Compose
- Required packages in requirements.txt

### Local Development Setup
1. Clone repository
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy .env.example to .env and configure:
   ```bash
   cp .env.example .env
   ```

### Running Locally with Docker
1. Build and start using local compose file:
   ```bash
   docker compose -f docker-compose.local.yml up -d --build
   ```
2. Monitor logs:
   ```bash
   docker compose -f docker-compose.local.yml logs -f
   ```
3. Access admin interface:
   ```
   http://localhost:5000
   ```

### Production Deployment
1. Ensure all changes are committed and pushed
2. Deploy using production compose file:
   ```bash
   docker compose up -d
   ```

## Common Development Tasks

### Adding New Cities
1. Update teams.yml with new team-to-city mappings
2. Format: 
   ```yaml
   cities:
     milano:
       - Inter
       - Milan
   ```

### Modifying Notification Times
1. Edit scheduler.py
2. Modify the hour check in send_morning_notifications
3. Default is set to 7 AM CET

### Manual Notifications
1. Use admin interface "Notify" button
2. Respects 5-minute cooldown between notifications
3. Tracks manual notifications separately
4. Prevents notification spam

### Testing Notifications
1. Use admin interface "Test Notify" button
2. Subject to same rate limiting as manual notifications
3. Check logs for delivery status
4. Verify notification timestamps

### Updating Database Schema
1. Add new columns to model classes in storage.py
2. Include upgrade logic in _upgrade_schema method
3. Ensure backward compatibility
4. Handle timezone-aware fields properly

### Adding Bot Commands
1. Create command handler in bot.py
2. Register handler in run_bot function
3. Update conversation handlers if needed
4. Test with both new and existing users

## Debugging

### Event Loop Issues
1. Check for multiple event loop instances
2. Verify nest_asyncio is properly initialized
3. Monitor send_message_sync operations
4. Check loop cleanup in async functions

### Notification Issues
1. Check scheduler logs for timing
2. Verify notification timestamps
3. Check rate limiting status
4. Confirm match data is being fetched
5. Verify timezone handling

### Database Issues
1. Inspect bot.db in data directory
2. Use SQLite browser for direct access
3. Check column types and constraints
4. Verify timezone-aware fields
5. Check notification timestamps

### Docker Issues
1. Check container logs
2. Verify volume mounts
3. Ensure proper cleanup between builds
4. Monitor resource usage

## Best Practices

1. Always use local Docker setup for testing
2. Handle async operations carefully
3. Use timezone-aware datetime objects
4. Implement proper rate limiting
5. Maintain backward compatibility
6. Document significant changes
7. Keep error handling consistent
8. Use proper type hints
9. Follow Flask best practices in admin
10. Manage event loops properly

## Configuration

### Environment Variables
Required in .env file:
- TELEGRAM_BOT_TOKEN: Your bot token
- ADMIN_PORT: Port for admin interface
- ADMIN_USERNAME: Admin login username
- ADMIN_PASSWORD: Admin login password
- FOOTBALL_API_TOKEN: Football data API token

### Docker Volumes
- data/: Contains SQLite database
- static/: Static files for admin interface
