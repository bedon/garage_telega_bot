import random
import pkgutil
import importlib
import inspect
from utils import randomize_status

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from handlers.instagram_handler import InstagramHandler
from handlers.facebook_handler import FacebookHandler
from handlers.twitter_handler import TwitterHandler
from handlers.tiktok_handler import TikTokHandler

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'
TOKEN_TEST = '7259399630:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'

all_handlers = [
    InstagramHandler(),
    FacebookHandler(),
    TwitterHandler(),
    TikTokHandler()
]

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)

    try:
        for handler_instance in all_handlers:
            if handler_instance.can_handle(message):
                await handler_instance.handle(update, message, user_prefix)
                return

    except Exception as e:
        print(f"Помилка обробки повідомлення: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()
