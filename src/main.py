import random
import pkgutil
import importlib
import inspect

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import handlers

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'
TOKEN_TEST = '7259399630:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'

async def randomize_status(user_name: str, chat_id: int) -> str:
    if not hasattr(randomize_status, "_chat_states"):
        randomize_status._chat_states = {}

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

all_handlers = []

for loader, module_name, is_pkg in pkgutil.iter_modules(handlers.__path__):
    module = importlib.import_module(f"handlers.{module_name}")

    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            all_handlers.append(obj)

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)

    try:
        for h in all_handlers:
            if h.can_handle(message):
                await h.handle(update, message, user_prefix)
                return

    except Exception as e:
        print(f"Помилка обробки повідомлення: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()
