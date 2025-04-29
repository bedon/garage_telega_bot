from telegram import Update

class MessageHandler:
    @staticmethod
    async def delete_message(update: Update) -> None:
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Не вдалося видалити повідомлення: {e}")
