import os, time
from pathlib import Path
from typing import List

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / '.env')

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from fireworks_client import stream_chat_messages, MODEL
from db import (
    Session, init_db, fetch_history, append_pair,
    get_persona, set_persona, reset_chat, DEFAULT_SYSTEM_PROMPT
)

TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")  # type: ignore
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is missing. Put it in your .env file.")

# --- commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "Hi! I remember context across restarts now.\n"
            "• /system <persona>  — change my style\n"
            "• /reset             — clear memory/persona\n"
            "• /model             — show current model"
        )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("pong")

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(f"Current model:\n`{MODEL}`", parse_mode="Markdown")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None or not update.message:
        return
    async with Session() as session:
        await reset_chat(session, chat_id)
    await update.message.reply_text("Memory and persona cleared.")

async def cmd_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None or not update.message:
        return
    new_prompt = " ".join(context.args) if context.args else ""
    async with Session() as session:
        if not new_prompt:
            persona = await get_persona(session, chat_id)
            await update.message.reply_text(
                "Usage: /system <new persona prompt>\n"
                f"Current: {persona}"
            )
            return
        await set_persona(session, chat_id, new_prompt)
    await update.message.reply_text("Persona updated.")

# --- chat handler (streams + DB history) ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    user_text = update.message.text.strip()

    if update.effective_chat is not None:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    
    msg = await update.message.reply_text("…")

    async with Session() as session:
        system_prompt = await get_persona(session, chat_id)
        history: List[dict] = await fetch_history(session, chat_id, limit_pairs=6)

        # Compose system + history + new user msg
        messages = [{"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        rendered = ""
        last_edit_t = 0.0
        CHARS_PER_EDIT = 80
        MIN_INTERVAL = 0.35

        try:
            async for delta in stream_chat_messages(messages):
                rendered += delta
                now = time.monotonic()
                if (len(rendered) % CHARS_PER_EDIT == 0) or (now - last_edit_t > MIN_INTERVAL):
                    last_edit_t = now
                    try:
                        await msg.edit_text(rendered + "▌")
                    except Exception:
                        pass

            await msg.edit_text(rendered or "…")
            await append_pair(session, chat_id, user_text, rendered)

        except Exception as e:
            await msg.edit_text(f"⚠️ Error talking to model: {e}")

# --- boot ---
async def on_startup(app: Application):
    await init_db()

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("system", cmd_system))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
