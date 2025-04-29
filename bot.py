import random
import re
import requests
import os
import tempfile
import subprocess
import time
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = '7736052370:AAEDIWcJAijCvzaoNLtNhKXEla_7orW93Kc'
TOKEN_TEST = '7259399630:AAEAnLGOBk7JkToma9Xh-i8oGoKDUmbGW2o'
INSTAGRAM_LINKS = ["https://www.instagram.com/reel/", "https://www.instagram.com/p/"]
TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/"]

async def god_or_gay(user_name: str) -> str:
    if user_name.lower() == "bogdan":
        return "👑 GOD DETECTED 👑\n" + user_name + "\n"
    else:
        return "🌈 " + "GAY DETECTED 💦" + "\n" + user_name + "\n"

async def randomize_status(user_name: str, chat_id: int) -> str:
    # Initialize chat state if not exists
    if not hasattr(randomize_status, "_chat_states"):
        randomize_status._chat_states = {}
    
    # Initialize state for this chat if not exists
    if chat_id not in randomize_status._chat_states:
        randomize_status._chat_states[chat_id] = {
            "last_user": None,
            "streak": 0
        }
    
    chat_state = randomize_status._chat_states[chat_id]
    
    if user_name == chat_state["last_user"]:
        chat_state["streak"] += 1
    else:
        chat_state["last_user"] = user_name
        chat_state["streak"] = 1

    if chat_state["streak"] >= 3:
        status = "🌈 GAY SPAMMER 💦💦💦\n"
    else:
        status = random.choice(["👑 NICE GUY 👑\n", "😎 CHILL GUY 🚬\n", "COOL DUDE 🤘\n", "FUNNY DUDE 🤣\n"])

    return f"{status} {user_name}"

async def handle_instagram(update: Update, message: str, sender_name: str) -> None:
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)
    
    try:
        # Видобуваємо ID поста з посилання
        instagram_id = re.search(r'/(?:p|reel)/([^/?]+)', message)
        if not instagram_id:
            # Не валідне посилання, повертаємо помилку але не видаляємо повідомлення користувача
            await update.message.chat.send_message(f"{user_prefix}📸 From Instagram\n\n[Невірне посилання Instagram] {message}")
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
                    caption=f"{user_prefix}{instagram_link}",
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
                            caption=f"{user_prefix}{instagram_link}",
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
                            caption=f"{user_prefix}{instagram_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        return
                    elif data.get("media_type") == "image":
                        # Відправляємо фото і тільки потім видаляємо повідомлення користувача
                        await update.message.chat.send_photo(
                            photo=data["download_url"], 
                            caption=f"{user_prefix}{instagram_link}",
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
                    caption=f"{user_prefix}{instagram_link}",
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
                    caption=f"{user_prefix}{instagram_link}",
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
            f"{user_prefix}{instagram_link}\n\n"
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
            f"{user_prefix}<a href='{message}'>📸 From Instagram</a>\n\n"
            f"Помилка при обробці відео. Спробуйте самостійно скачати через:\n\n"
            f"1. https://saveinsta.app/\n"
            f"2. https://instadownloader.co/\n\n"
            f"Оригінальне посилання: {message}",
            parse_mode="HTML"
        )

async def handle_tiktok(update: Update, message: str, sender_name: str) -> None:
    chat_id = update.message.chat_id
    user_prefix = await randomize_status(sender_name, chat_id)
    
    # Створюємо посилання в HTML форматі
    tiktok_link = f'<a href="{message}">🎵 From TikTok</a>'

    try:
        api_url = "https://tikwm.com/api/"
        params = {"url": message}
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()

        if data.get("code") == 0 and data.get("data", {}).get("play"):
            video_url = data["data"]["play"]
            await update.message.chat.send_video(
                video=video_url, 
                caption=f"{user_prefix}{tiktok_link}",
                parse_mode="HTML"
            )
            await delete_message(update)
            return
        else:
            # Спробуємо альтернативний API
            try:
                api_url = "https://api.tiktokdownload.com/api"
                params = {"url": message}
                response = requests.get(api_url, params=params, timeout=15)
                data = response.json()
                
                if data.get("success") and data.get("video_url"):
                    await update.message.chat.send_video(
                        video=data["video_url"], 
                        caption=f"{user_prefix}{tiktok_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                # Продовжуємо, без логування помилки
                pass
                
            # Якщо обидва API не вдалося використати, відправляємо повідомлення без видалення
            await update.message.chat.send_message(
                f"{user_prefix}{tiktok_link}\n\n[Не вдалося отримати відео]",
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"Помилка обробки TikTok відео: {e}")
        await update.message.chat.send_message(
            f"{user_prefix}{tiktok_link}\n\n[Помилка при завантаженні відео]",
            parse_mode="HTML"
        )

async def delete_message(update: Update) -> None:
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Не вдалося видалити повідомлення: {e}")

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    message = update.message.text
    sender_name = update.message.from_user.full_name

    try:
        # Перевірка Instagram посилань
        if any(link in message for link in INSTAGRAM_LINKS):
            await handle_instagram(update, message, sender_name)
            return

        # Перевірка TikTok посилань
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