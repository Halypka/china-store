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

3. Copy `.env.example` to `.env`. Set `BOT_TOKEN`, your numeric `ADMIN_ID`, and `SUPPORT_USERNAME` (without `@`). The support screen links customers to that manager account.
4. Start the bot:

   ```powershell
   py bot.py
   ```

The bot creates `china_store.sqlite3` on first run. It stores the order counter, selected languages, admin reply mappings, and requests there. Keep the database file between restarts.

Customers send product links or photos from **Catalog**. Each request appears in the admin chat with **Approve** and **Decline** buttons. Approving or declining notifies the customer, and the current status appears in **My requests**. After approving, reply to the request card with the payment details; the bot forwards your reply to the customer. Customers can change their language at any time from the **Language** menu button.

## Windows executable

Every push to the bot branch builds `ChinaStoreBot.exe` in GitHub Actions. Download the `ChinaStoreBot-windows` artifact from the workflow run, extract it, copy `.env.example` to `.env`, fill in the bot settings, and run `ChinaStoreBot.exe`. Keep `.env` and `china_store.sqlite3` next to the executable; do not upload `.env` to GitHub.

To install a newer version later, stop the bot and double-click `Обновить бота.bat` in the same folder as `ChinaStoreBot.exe`. The updater downloads the latest public Windows release and replaces only the executable and `.env.example`; it keeps your `.env` and order database. An internet connection is required.

