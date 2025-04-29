import random

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from handlers.instagram_handler import handle_instagram
from handlers.tiktok_handler import handle_tiktok

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'
TOKEN_TEST = '7259399630:AAEAnLGOBk7JkToma9Xh-i8oGoKDUmbGW2o'
INSTAGRAM_LINKS = ["https://www.instagram.com/reel/", "https://www.instagram.com/p/"]
TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/"]

async def randomize_status(user_name: str, chat_id: int) -> str:
    # Initialize chat state if not exists
    if not hasattr(randomize_status, "_chat_states"):
        randomize_status._chat_states = {}
    
    # Initialize state for this chat if not exists
    if chat_id not in randomize_status._chat_states:
        randomize_status._chat_states[chat_id] = {
            "last_user": None,
            "streak": 0
        }
    
    chat_state = randomize_status._chat_states[chat_id]
    
    if user_name == chat_state["last_user"]:
        chat_state["streak"] += 1
    else:
        chat_state["last_user"] = user_name
        chat_state["streak"] = 1

    if chat_state["streak"] >= 3:
        status = "🌈 GAY SPAMMER 💦💦💦\n"
    else:
        status = random.choice(["👑 NICE GUY 👑\n", "😎 CHILL GUY 🚬\n", "COOL DUDE 🤘\n", "FUNNY DUDE 🤣\n"])

    return f"{status} {user_name}"

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)

    try:
        # Перевірка Instagram посилань
        if any(link in message for link in INSTAGRAM_LINKS):
            await handle_instagram(update, message, user_prefix)
            return

        # Перевірка TikTok посилань
        if any(link in message for link in TIKTOK_LINKS):
            await handle_tiktok(update, message, user_prefix)
            return

    except Exception as e:
        print(f"Помилка обробки повідомлення: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()