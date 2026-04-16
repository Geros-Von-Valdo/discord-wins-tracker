# Discord Wins Tracker

A professional Discord bot designed to track game victories and log them into a Google Sheets database. It includes a built-in Keep-Alive system to ensure 24/7 uptime on free-tier hosting services.

## Features

- **Automated Logging:** Use the `/win` command to record victories.
- **Mention Support:** Automatically detects `@user` tags in messages to attribute wins to specific players.
- **Personal History:** Access `/mywins` to view a paginated list of your past victories.
- **Global Leaderboard:** Use `/leaderboard` to view the top players across all game categories.
- **Google Sheets Integration:** Acts as a transparent, easy-to-manage database.
- **Uptime Optimization:** Background Flask server to prevent hosting provider hibernation.

## Technical Architecture

The bot uses a hybrid infrastructure to remain active without costs:
1. **Flask (Web Server):** A lightweight server running in a separate thread.
2. **UptimeRobot (Pinger):** An external service that hits the Flask endpoint every 5 minutes, resetting the inactivity timer on the hosting platform (Render).

## Tech Stack

- **Language:** Python 3.10+
- **API Wrapper:** discord.py
- **Database Wrapper:** gspread
- **Web Framework:** Flask
- **Environment Management:** python-dotenv

## Setup Instructions

### 1. Local Environment
Clone the repository and install dependencies:
```bash
git clone https://github.com/Geros-Von-Valdo/discord-wins-tracker.git
pip install -r requirements.txt
```

### 2. Configuration
Create a .env file in the root directory:
```bash
DISCORD_TOKEN=your_token
PLANILHA_ID=your_sheet_id
GOOGLE_CREDENTIALS='{"type": "service_account", ...}'
```

### 3. Configuration
When deploying to Render:

-Build Command: pip install -r requirements.txt

-Start Command: python win_counter.py

-Environment Variables: Set DISCORD_TOKEN, PLANILHA_ID, and GOOGLE_CREDENTIALS in the dashboard.

### Security

Sensitive data is managed via Environment Variables. Ensure that .env is never committed to version control.