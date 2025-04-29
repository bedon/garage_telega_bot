import io
import os
import re
import subprocess
import tempfile

import requests
from telegram import Update

from handlers.message_handler import delete_message


async def handle_instagram(update: Update, message: str, sender_name: str) -> None:
    try:
        # Видобуваємо ID поста з посилання
        instagram_id = re.search(r'/(?:p|reel)/([^/?]+)', message)
        if not instagram_id:
            # Не валідне посилання, повертаємо помилку але не видаляємо повідомлення користувача
            await update.message.chat.send_message(
                f"{sender_name} 📸 From Instagram\n\n[Невірне посилання Instagram] {message}")
            return

        instagram_id = instagram_id.group(1)

        # Створюємо посилання в HTML форматі
        instagram_link = f'<a href="{message}">📸 From Instagram</a>'

        # МЕТОД 1: Використання yt-dlp для скачування відео напряму (найнадійніший)
        try:
            # Скачуємо відео безпосередньо в пам'ять, без створення проміжного файлу
            process = subprocess.run(
                ["yt-dlp", "-o", "-", "--format", "best", message],
                capture_output=True,
                check=False  # Дозволяємо продовжувати навіть якщо є помилка
            )

            # Перевіряємо, чи отримали дані
            if process.stdout and len(process.stdout) > 0:
                video_bytes = io.BytesIO(process.stdout)
                video_bytes.seek(0)

                # Відправляємо відео і тільки потім видаляємо повідомлення користувача
                await update.message.chat.send_video(
                    video=video_bytes,
                    caption=f"{sender_name} {instagram_link}",
                    parse_mode="HTML"
                )
                await delete_message(update)
                return
            else:
                # Продовжуємо до наступного методу, без логування помилки
                pass
        except Exception as e:
            # Спробуємо через тимчасовий файл, якщо не вдалося напряму
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f"{instagram_id}.mp4")

                process = subprocess.run(
                    ["yt-dlp", "-o", output_path, "--format", "best", message],
                    capture_output=True,
                    text=True,
                    check=False
                )

                # Перевіряємо, чи файл був створений
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as video_file:
                        # Відправляємо відео і тільки потім видаляємо повідомлення користувача
                        await update.message.chat.send_video(
                            video=video_file,
                            caption=f"{sender_name} {instagram_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        # Видаляємо тимчасовий файл після надсилання
                        os.remove(output_path)
                        return
            except Exception:
                # Продовжуємо до наступного методу, без логування помилки
                pass

        # МЕТОД 2: Використання instagram-stories-api (надійний Vercel API)
        try:
            api_url = f"https://instagram-stories-api.vercel.app/api/post?url={message}"
            response = requests.get(api_url, timeout=20)

            if response.status_code == 200:
                data = response.json()
                if data.get("error") is None and data.get("media_type") and data.get("download_url"):
                    if data.get("media_type") == "video":
                        # Відправляємо відео і тільки потім видаляємо повідомлення користувача
                        await update.message.chat.send_video(
                            video=data["download_url"],
                            caption=f"{sender_name} {instagram_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        return
                    elif data.get("media_type") == "image":
                        # Відправляємо фото і тільки потім видаляємо повідомлення користувача
                        await update.message.chat.send_photo(
                            photo=data["download_url"],
                            caption=f"{sender_name} {instagram_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        return
        except Exception:
            # Продовжуємо до наступного методу, без логування помилки
            pass

        # МЕТОД 3: Проба фетчу з direct інстаграм URL (останній метод, зазвичай працює)
        try:
            # Спробуємо отримати лінк прямо з сторiнки Instagram
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }

            response = requests.get(message, headers=headers, timeout=15)
            # Пошук посилання на відео за допомогою регулярного виразу
            video_pattern = r'video_url":"([^"]+)"'
            image_pattern = r'display_url":"([^"]+)"'

            video_match = re.search(video_pattern, response.text)
            if video_match:
                video_url = video_match.group(1).replace("\\u0026", "&")
                # Відправляємо відео і тільки потім видаляємо повідомлення користувача
                await update.message.chat.send_video(
                    video=video_url,
                    caption=f"{sender_name} {instagram_link}",
                    parse_mode="HTML"
                )
                await delete_message(update)
                return

            image_match = re.search(image_pattern, response.text)
            if image_match:
                image_url = image_match.group(1).replace("\\u0026", "&")
                # Відправляємо фото і тільки потім видаляємо повідомлення користувача
                await update.message.chat.send_photo(
                    photo=image_url,
                    caption=f"{sender_name} {instagram_link}",
                    parse_mode="HTML"
                )
                await delete_message(update)
                return
        except Exception:
            # Продовжуємо до резервного методу, без логування помилки
            pass

        # ОСТАННІЙ РЕЗЕРВНИЙ ВАРІАНТ: Надаємо корисні посилання для скачування
        # Не видаляємо повідомлення користувача, оскільки ми не змогли скачати відео
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
        # Не видаляємо повідомлення користувача, оскільки сталася помилка
        await update.message.chat.send_message(
            f"{sender_name} <a href='{message}'>📸 From Instagram</a>\n\n"
            f"Помилка при обробці відео. Спробуйте самостійно скачати через:\n\n"
            f"1. https://saveinsta.app/\n"
            f"2. https://instadownloader.co/\n\n"
            f"Оригінальне посилання: {message}",
            parse_mode="HTML"
        )