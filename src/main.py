import os
from dotenv import load_dotenv
from utils import randomize_status, load_handlers

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set")

# Initialize all handlers
all_handlers = load_handlers()

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)

    try:
        # Try to handle the message with each handler
        for handler_instance in all_handlers:
            if handler_instance.can_handle(message):
                await handler_instance.handle(update, message, user_prefix)
                return

    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    # Initialize and run the bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()
