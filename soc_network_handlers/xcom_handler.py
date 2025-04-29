import io
import subprocess
import tempfile
import os

from telegram import Update
from message_handler import MessageHandler

class TwitterHandler:
    TWITTER_LINKS = ["https://x.com/", "https://twitter.com/"]

    @staticmethod
    def can_handle(message: str) -> bool:
        return any(link in message for link in TwitterHandler.TWITTER_LINKS)

    @staticmethod
    async def handle(update: Update, message: str, sender_name: str) -> None:
        try:
            twitter_link = f'<a href="{message}">🐦 From Twitter (X)</a>'

            # Попытка скачать через yt-dlp напрямую в память
            try:
                process = subprocess.run(
                    ["yt-dlp", "-o", "-", "--format", "best", message],
                    capture_output=True,
                    check=False
                )

                if process.stdout and len(process.stdout) > 0:
                    video_bytes = io.BytesIO(process.stdout)
                    video_bytes.seek(0)

                    await update.message.chat.send_video(
                        video=video_bytes,
                        caption=f"{sender_name} {twitter_link}",
                        parse_mode="HTML"
                    )
                    await MessageHandler.delete_message(update)
                    return
            except Exception:
                pass

            # Попытка скачать через временный файл
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "twitter_video.mp4")

                process = subprocess.run(
                    ["yt-dlp", "-o", output_path, "--format", "best", message],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as video_file:
                        await update.message.chat.send_video(
                            video=video_file,
                            caption=f"{sender_name} {twitter_link}",
                            parse_mode="HTML"
                        )
                        await MessageHandler.delete_message(update)
                        os.remove(output_path)
                        return
            except Exception:
                pass

            # Если ничего не получилось
            await update.message.chat.send_message(
                f"{sender_name} {twitter_link}\n\n"
                f"Не вдалося автоматично скачати відео.\n"
                f"Спробуйте самостійно через:\n\n"
                f"1. https://ssstwitter.com/\n"
                f"2. https://twdown.net/\n"
                f"3. https://twitsave.com/\n\n"
                f"Оригінальне посилання: {message}",
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Помилка обробки Twitter відео: {e}")
            await update.message.chat.send_message(
                f"{sender_name} {twitter_link}\n\n"
                f"Помилка при обробці відео. Спробуйте самостійно через:\n\n"
                f"1. https://ssstwitter.com/\n"
                f"2. https://twdown.net/\n"
                f"3. https://twitsave.com/\n\n"
                f"Оригінальне посилання: {message}",
                parse_mode="HTML"
            )
