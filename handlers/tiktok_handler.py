import requests
from telegram import Update

from handlers.message_handler import delete_message


async def handle_tiktok(update: Update, message: str, sender_name: str) -> None:
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
                caption=f"{sender_name} {tiktok_link}",
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
                        caption=f"{sender_name} {tiktok_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                # Продовжуємо, без логування помилки
                pass

            # Якщо обидва API не вдалося використати, відправляємо повідомлення без видалення
            await update.message.chat.send_message(
                f"{sender_name} {tiktok_link}\n\n[Не вдалося отримати відео]",
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"Помилка обробки TikTok відео: {e}")
        await update.message.chat.send_message(
            f"{sender_name} {tiktok_link}\n\n[Помилка при завантаженні відео]",
            parse_mode="HTML"
        )