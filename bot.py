import random

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'
TOKEN_TEST = '7259399630:AAEAnLGOBk7JkToma9Xh-i8oGoKDUmbGW2o'
INSTAGRAM_REEL = "https://www.instagram.com/reel/"
TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/"]

async def god_or_gay(user_name: str) -> str:
    if user_name.lower() == "bogdan":
        return "👑 GOD DETECTED 👑\n" + user_name + "\n"
    else:
        return "🌈 " + "GAY DETECTED 💦💦💦" + "\n" + user_name + "\n"

async def randomize_status(user_name: str) -> str:
    if not hasattr(randomize_status, "_last"):
        randomize_status._last = None
        randomize_status._streak = 0

    if user_name == randomize_status._last:
        randomize_status._streak += 1
    else:
        randomize_status._last = user_name
        randomize_status._streak = 1

    if randomize_status._streak >= 3:
        status = "🌈 GAY SPAMMER 💦💦💦\n"
    else:
        status = random.choice(["👑 GOD 👑\n", "😎 CHILL GUY 🚬\n"])

    return f"{status} {user_name}"

async def delete_message(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Не вдалося видалити повідомлення: {e}")

async def handle_instagram(update: Update, message: str, sender_name: str) -> None:
    new_message = f"{await randomize_status(sender_name)} 📸 From Instagram:\n\n" + message.replace(
        "instagram", "ddinstagram"
    )
    await delete_message(update)
    await update.message.chat.send_message(new_message)

async def handle_tiktok(update: Update, message: str, sender_name: str) -> None:
    await delete_message(update)
    user_prefix = await randomize_status(sender_name)

    try:
        api_url = "https://tikwm.com/api/"
        params = {"url": message}
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()

        if data.get("code") == 0:
            video_url = data["data"]["play"]
            await update.message.chat.send_video(video=video_url, caption=f"{user_prefix}🎵 From TikTok")
        else:
            print(f"TikTok API error: {data}")
            await update.message.chat.send_message(f"{user_prefix}🎵 From TikTok\n\n[Не вдалося отримати відео] {message}")

    except Exception as e:
        print(f"Помилка обробки TikTok відео: {e}")
        await update.message.chat.send_message(f"{user_prefix}🎵 From TikTok\n\n[Помилка при завантаженні відео] {message}")

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name

    try:
        if INSTAGRAM_REEL in message:
            await handle_instagram(update, message, sender_name)
            return

        if any(link in message for link in TIKTOK_LINKS):
            await handle_tiktok(update, message, sender_name)
            return

    except Exception as e:
        print(f"Помилка обробки повідомлення: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == '__main__':
    main()