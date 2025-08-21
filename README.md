# Dobby Telegram Bot

A Telegram bot powered by [python-telegram-bot](https://docs.python-telegram-bot.org/), PostgreSQL, and Fireworks AI models.  
It responds to commands, stores chats in a Postgres database, and calls Fireworks AI (dobby-unhinged-llama-3-3-70b-new) for completions.

---

## 🚀 Features

- `/ping` → replies with `pong`
- `/start` → initializes user profile
- Stores messages in PostgreSQL using SQLAlchemy + asyncpg
- Calls Fireworks AI models for responses
- Configuration via `.env` file

---

## 🛠️ Requirements

- Python **3.12+**
- PostgreSQL **16+**

---

## 📦 Setup (Local Development)

1. **Clone the repo**

   ```bash
   git clone https://github.com/akglali/<dobby_telegram_bot.git
   cd dobby_telegram_bot
   ```

2. **Create and activate virtualenv**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**

   ```bash
   # log into postgres (Linux/Mac)
   psql -U postgres

   CREATE USER dobby WITH PASSWORD 'change_me_strong';
   CREATE DATABASE dobbydb OWNER dobby;
   GRANT ALL PRIVILEGES ON DATABASE dobbydb TO dobby;
   \q
   ```

5. **Create `.env` file**

   In the project root (next to `app.py`), create `.env`:

   ```env
   TELEGRAM_TOKEN=123456:YOUR_TELEGRAM_BOT_TOKEN
   DOBBY_API_KEY=fwk_XXXXXXXXXXXXXXXXXXXXXXXX
   DOBBY_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
   DATABASE_URL=postgresql://dobby:change_me_strong@localhost:5432/dobbydb
   ```

6. **Initialize the database (optional)**

   Run the checker to ensure DB connection + create tables:

   ```bash
   python db_check.py
   ```

   You should see `OK: engine connected.` and `OK: tables ensured.`

7. **Run the bot**

   ```bash
   python app.py
   ```

   Open Telegram, message your bot `/ping`, and you should get `pong`.

---

## 🐘 Notes

- The bot uses **polling**, so you don’t need to open ports.
- If you want to run it on a server, you can use `systemd` or `pm2` to keep it running.
- PostgreSQL URL must use the `postgresql://` scheme (not `postgres://`).

---
