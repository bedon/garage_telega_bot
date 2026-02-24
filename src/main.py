import os
from dotenv import load_dotenv
from utils import randomize_status, load_handlers
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Set up logger (LOG_LEVEL=INFO or DEBUG for verbose output)
log_level = os.getenv("LOG_LEVEL", "ERROR").upper()
numeric_level = getattr(logging, log_level, logging.ERROR)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=numeric_level,
)

logger = logging.getLogger(__name__)

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
    sender = update.message.from_user
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender, chat_id)

    try:
        # Try to handle the message with each handler
        for handler_instance in all_handlers:
            if handler_instance.can_handle(message):
                await handler_instance.handle(update, message, user_prefix)
                return

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

def main():
    # Initialize and run the bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()
