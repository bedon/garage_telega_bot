import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

import config
from utils import load_handlers, randomize_status

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.ERROR),
)
# httpx logs every Telegram poll at INFO; keep it quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

all_handlers = load_handlers()


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    # Streak tracking counts every message, not only links.
    user_prefix = await randomize_status(update.message.from_user, update.message.chat_id)
    handler_instance = next((h for h in all_handlers if h.can_handle(message)), None)
    if handler_instance is None:
        return

    try:
        await handler_instance.handle(update, message, user_prefix)
    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)


def main():
    if not config.TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set")

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .media_write_timeout(120)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()


if __name__ == "__main__":
    main()
