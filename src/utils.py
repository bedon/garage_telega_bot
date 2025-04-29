import random
from telegram import Update

async def delete_message(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Failed to delete message: {e}")

async def randomize_status(user_name: str, chat_id: int) -> str:
    # Initialize chat states if not exists
    if not hasattr(randomize_status, "_chat_states"):
        randomize_status._chat_states = {}

    # Initialize or get chat state for current chat
    if chat_id not in randomize_status._chat_states:
        randomize_status._chat_states[chat_id] = {
            "last_user": None,
            "streak": 0
        }

    chat_state = randomize_status._chat_states[chat_id]

    # Update streak counter
    if user_name == chat_state["last_user"]:
        chat_state["streak"] += 1
    else:
        chat_state["last_user"] = user_name
        chat_state["streak"] = 1

    # Determine status based on streak
    if chat_state["streak"] >= 3:
        status = "🌈 GAY SPAMMER 💦💦💦\n"
    else:
        status = random.choice(["👑 NICE GUY 👑\n", "😎 CHILL GUY 🚬\n", "COOL DUDE 🤘\n", "FUNNY DUDE 🤣\n"])

    return f"{status} {user_name}"
