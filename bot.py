from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from gay_colorizer import *

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'

def god_or_gay(user_name: str) -> str:
    return "GAY GOD DETECTED 🌈\n" + user_name + "\n" if user_name.lower() == "bogdan" else colorize_gay("GAY DETECTED") + "\n" + user_name + "\n"

async def replace_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    sender_name = update.message.from_user.full_name
    if "https://www.instagram.com/reel/" in message:
        # Заменяем ссылку
        new_message = god_or_gay(sender_name) + "\n" + message.replace(
            "instagram",
            "ddinstagram"
        )

        # Удаляем оригинальное сообщение
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

        # Отправляем исправленное сообщение
        await update.message.chat.send_message(new_message)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Добавляем обработчик всех текстовых сообщений (кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, replace_instagram_link))

    app.run_polling()

if __name__ == '__main__':
    main()
