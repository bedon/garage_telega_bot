import random
import importlib
import pkgutil
import inspect
from telegram import Update, User

async def delete_message(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Failed to delete message: {e}")

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

    return f"by <a href=\"tg://user?id={user.id}\">{user.full_name}</a> {status}\n"

def load_handlers():
    """
    Automatically discovers and loads all handler classes from the handlers directory.
    Returns a list of instantiated handler objects.
    """
    handlers = []
    handlers_package = "handlers"
    
    # Import the handlers package
    handlers_module = importlib.import_module(handlers_package)
    
    # Iterate through all modules in the handlers package
    for _, module_name, _ in pkgutil.iter_modules(handlers_module.__path__):
        # Import the module
        module = importlib.import_module(f"{handlers_package}.{module_name}")
        
        # Find all classes in the module that end with 'Handler'
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.endswith('Handler') and obj.__module__ != 'handlers':
                # Instantiate the handler and add it to the list
                handlers.append(obj())
    
    return handlers
