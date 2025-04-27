from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = 'твой_токен_сюда'

async def replace_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text

    if "https://www.instagram.com/reel/" in message:
        # Заменяем ссылку
        new_message = message.replace(
            "https://www.instagram.com/reel/",
            "https://www.ddinstagram.com/reel/"
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
