# China Store Telegram bot

Telegram bot for personal shopping from China with delivery across Europe.

## Setup

1. Use Python 3.10 or newer.
2. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set `BOT_TOKEN`. `ADMIN_ID` defaults to the existing project admin ID (`9214809528`); set it only if that ID should change.
4. Start the bot:

   ```powershell
   py bot.py
   ```

The bot creates `china_store.sqlite3` on first run. It stores the order counter, selected languages, and admin reply mappings there. Keep the database file between restarts.
