import io
import os
import re
import subprocess
import tempfile

import requests
from telegram import Update

from message_handler import MessageHandler


class InstagramHandler:
    INSTAGRAM_LINKS = ["https://www.instagram.com/reel/", "https://www.instagram.com/p/"]

    @staticmethod
    def can_handle(message: str) -> bool:
        return any(link in message for link in InstagramHandler.INSTAGRAM_LINKS)

    @staticmethod
    async def handle(update: Update, message: str, sender_name: str) -> None:
        try:
            instagram_id_match = re.search(r'/(?:p|reel)/([^/?]+)', message)
            if not instagram_id_match:
                await update.message.chat.send_message(
                    f"{sender_name} 📸 From Instagram\n\n[Невірне посилання Instagram] {message}"
                )
                return

            instagram_id = instagram_id_match.group(1)
            instagram_link = f'<a href="{message}">📸 From Instagram</a>'

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
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await MessageHandler.delete_message(update)
                    return
            except Exception:
                pass

            # Попытка скачать через временный файл
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f"{instagram_id}.mp4")

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
                            caption=f"{sender_name} {instagram_link}",
                            parse_mode="HTML"
                        )
                        await MessageHandler.delete_message(update)
                        os.remove(output_path)
                        return
            except Exception:
                pass

            # Попытка через сторонний API
            try:
                api_url = f"https://instagram-stories-api.vercel.app/api/post?url={message}"
                response = requests.get(api_url, timeout=20)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error") is None and data.get("download_url"):
                        if data.get("media_type") == "video":
                            await update.message.chat.send_video(
                                video=data["download_url"],
                                caption=f"{sender_name} {instagram_link}",
                                parse_mode="HTML"
                            )
                            await MessageHandler.delete_message(update)
                            return
                        elif data.get("media_type") == "image":
                            await update.message.chat.send_photo(
                                photo=data["download_url"],
                                caption=f"{sender_name} {instagram_link}",
                                parse_mode="HTML"
                            )
                            await MessageHandler.delete_message(update)
                            return
            except Exception:
                pass

            # Последняя попытка — парсинг исходной страницы
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "max-age=0"
                }

                response = requests.get(message, headers=headers, timeout=15)

                video_match = re.search(r'video_url":"([^"]+)"', response.text)
                if video_match:
                    video_url = video_match.group(1).replace("\\u0026", "&")
                    await update.message.chat.send_video(
                        video=video_url,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await MessageHandler.delete_message(update)
                    return

                image_match = re.search(r'display_url":"([^"]+)"', response.text)
                if image_match:
                    image_url = image_match.group(1).replace("\\u0026", "&")
                    await update.message.chat.send_photo(
                        photo=image_url,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await MessageHandler.delete_message(update)
                    return
            except Exception:
                pass

            # Если все методы провалились
            await update.message.chat.send_message(
                f"{sender_name} {instagram_link}\n\n"
                f"Не вдалося автоматично скачати відео. Спробуйте ці сервіси:\n\n"
                f"1. https://saveinsta.app/instagram-video-downloader/{instagram_id}\n"
                f"2. https://www.y2mate.com/instagram/{instagram_id}\n"
                f"3. https://sssinstagram.com/\n\n"
                f"Оригінальне посилання: {message}",
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Помилка обробки Instagram відео: {e}")
            await update.message.chat.send_message(
                f"{sender_name} <a href='{message}'>📸 From Instagram</a>\n\n"
                f"Помилка при обробці відео. Спробуйте самостійно скачати через:\n\n"
                f"1. https://saveinsta.app/\n"
                f"2. https://instadownloader.co/\n\n"
                f"Оригінальне посилання: {message}",
                parse_mode="HTML"
            )
