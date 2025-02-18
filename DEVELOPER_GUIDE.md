# Developer Guide

## Project Structure

```
partita-bot/
├── admin.py           # Admin interface for user management
├── bot.py            # Main bot implementation and command handlers
├── config.py         # Configuration and environment variables
├── fetcher.py        # Match fetching and filtering logic
├── scheduler.py      # Notification scheduling system
├── storage.py        # Database models and operations
├── teams.yml         # Team to city mapping configuration
├── requirements.txt  # Project dependencies
└── test/            # Test directory
    ├── test_api.py            # API fetch testing
    ├── test_cache_cleanup.py  # Cache maintenance testing
    ├── test_fetcher.py        # Match fetching testing
    ├── test_notification.py   # Notification system testing
    └── test_scheduler.py      # Scheduler functionality testing
```

## Core Components

### Database (storage.py)
- SQLite database with SQLAlchemy ORM
- Tables: users, access_control, and access_mode
- Handles user management and access control
- Tracks notification timestamps for each user

### Match Fetcher (fetcher.py)
- Interfaces with football-data.org API
- Caches responses for 7 days
- Maps teams to cities using teams.yml
- Auto-cleans old cache files

### Scheduler (scheduler.py)
- Runs hourly checks for each user
- Converts times to user's local timezone
- Sends notifications after 7 AM if matches found
- Prevents duplicate notifications on same day

### Bot (bot.py)
- Telegram bot command handlers
- User registration and settings
- Conversation flows for city/timezone setup
- Integrates scheduler for notifications

### Admin Interface (admin.py)
- Web interface for user management
- Access control (whitelist/blocklist)
- Manual notification triggers
- User activity monitoring

## Testing

### Test Suites
1. **test_api.py**: Verify API interactions
2. **test_cache_cleanup.py**: Cache management
3. **test_fetcher.py**: Match fetching logic
4. **test_notification.py**: Notification delivery
5. **test_scheduler.py**: Scheduling system

### Running Tests
```bash
cd test
python3 test_api.py          # Test API functionality
python3 test_fetcher.py      # Test match fetching
python3 test_notification.py # Test notification system
python3 test_scheduler.py    # Test scheduler
python3 test_cache_cleanup.py # Test cache maintenance
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
3. Default is set to 7 AM local time

### Testing Notifications
1. Use admin interface "Notify User" button
2. Or run test_notification.py
3. Check logs for delivery status

### Updating Database Schema
1. Add new columns to model classes in storage.py
2. Include upgrade logic in _upgrade_schema method
3. Ensure backward compatibility

### Adding Bot Commands
1. Create command handler in bot.py
2. Register handler in run_bot function
3. Update conversation handlers if needed

## Development Environment

### Requirements
- Python 3.10+
- SQLite3
- Required packages in requirements.txt

### Setup
1. Clone repository
2. Create virtual environment:
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

### Running Locally
1. Start bot:
   ```bash
   python bot.py
   ```
2. Access admin interface:
   ```
   http://localhost:5000
   ```

### Docker Deployment
1. Build image:
   ```bash
   docker build -t partita-bot .
   ```
2. Run container:
   ```bash
   docker-compose up -d
   ```

## Debugging

### Notification Issues
1. Check scheduler logs for timing
2. Verify user timezone settings
3. Confirm match data in cache
4. Check last_notification timestamps

### Database Issues
1. Inspect bot.db in data directory
2. Use SQLite browser for direct access
3. Check column types and constraints

### API Issues
1. Verify API token in config
2. Check cache files in data directory
3. Monitor rate limiting

## Best Practices

1. Always run tests before deploying
2. Use timezone-aware datetime objects
3. Handle API rate limits appropriately
4. Log meaningful debug information
5. Maintain backward compatibility
6. Document significant changes
7. Keep cache cleanup logic updated