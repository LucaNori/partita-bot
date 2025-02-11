# Partita Bot

A Telegram bot that notifies users about soccer matches in their city. The bot sends daily notifications at 7 AM if there are matches scheduled in the user's selected city.

## Features

- Daily notifications at 7 AM about soccer matches in the user's city
- User city preference management
- Admin interface for user management
- Access control with whitelist/blocklist support
- Docker deployment with GHCR support

## Prerequisites

- Python 3.11+
- Docker
- A Telegram Bot Token (get it from [@BotFather](https://t.me/botfather))

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/partita-bot.git
cd partita-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your configuration:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
ADMIN_PORT=5000
```

6. Run the bot:
```bash
python bot.py
```

## Docker Deployment

### Building Locally

1. Build the Docker image:
```bash
docker build -t partita-bot .
```

2. Run the container:
```bash
docker run -d \
  --name partita-bot \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  partita-bot
```

### Using GHCR (GitHub Container Registry)

1. Create a new release on GitHub with a semantic version (e.g., v1.0.0)

2. The GitHub Action will automatically build and push the image to GHCR

3. Pull and run the container:
```bash
docker pull ghcr.io/yourusername/partita-bot:latest
docker run -d \
  --name partita-bot \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  ghcr.io/yourusername/partita-bot:latest
```

## Bot Commands

- `/start` - Start the bot
- `/setcity [city]` - Set your city for match notifications
- `/check` - Manually check for matches in your city today
- `/help` - Show help message

## Admin Interface

The admin interface is available at `http://localhost:5000` (or your configured port). Use the credentials set in your `.env` file to log in.

Features:
- View all registered users
- Block/unblock users
- Switch between whitelist and blocklist modes
- Monitor user cities and registration dates

## GitHub Actions Workflow

The repository includes a GitHub Actions workflow that:
1. Builds the Docker image
2. Tags it with the release version and 'latest'
3. Pushes it to GitHub Container Registry (GHCR)

To use GHCR:
1. Generate a Personal Access Token (PAT) with `read:packages` and `write:packages` permissions
2. Add the PAT as a repository secret named `GHCR_TOKEN`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.