import html
import importlib
import inspect
import logging
import pkgutil
import random

from telegram import Update, User

logger = logging.getLogger(__name__)


async def delete_message(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning("Failed to delete message: %s", e)


async def randomize_status(user: User, chat_id: int) -> str:
    # Initialize chat states if not exists
    if not hasattr(randomize_status, "_chat_states"):
        randomize_status._chat_states = {}

    # Initialize or get chat state for current chat
    if chat_id not in randomize_status._chat_states:
        randomize_status._chat_states[chat_id] = {
            "last_user": user.id,
            "streak": 0
        }

    chat_state = randomize_status._chat_states[chat_id]

    # Update streak counter
    if user.id == chat_state["last_user"]:
        chat_state["streak"] += 1
    else:
        chat_state["last_user"] = user.id
        chat_state["streak"] = 1

    # Determine status based on streak
    if chat_state["streak"] >= 3:
        status = "🌈 GAY SPAMMER 💦💦💦\n"
    else:
        status = random.choice(["👑 NICE GUY 👑", "😎 CHILL GUY 🚬", "COOL DUDE 🤘", "FUNNY DUDE 🤣"])

    return f"by <a href=\"tg://user?id={user.id}\">{html.escape(user.full_name)}</a> {status}\n"


def load_handlers():
    """
    Automatically discovers and loads all handler classes from the handlers directory.
    Returns a list of instantiated handler objects.
    """
    handlers_module = importlib.import_module("handlers")
    base = handlers_module.BaseHandler
    handlers = []

    for _, module_name, _ in pkgutil.iter_modules(handlers_module.__path__):
        module = importlib.import_module(f"handlers.{module_name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            # Only classes defined in this module (skips imported BaseHandler etc.)
            if issubclass(obj, base) and obj is not base and obj.__module__ == module.__name__:
                handlers.append(obj())

    return handlers
