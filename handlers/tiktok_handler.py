import requests
from telegram import Update

from handlers.message_handler import MessageHandler


class TikTokHandler:
    TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/"]

    @staticmethod
    def can_handle(message: str) -> bool:
        return any(link in message for link in TikTokHandler.TIKTOK_LINKS)

    @staticmethod
    async def handle(update: Update, message: str, sender_name: str) -> None:
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
                await MessageHandler.delete_message(update)
                return
            else:
                # Пробуем альтернативный API
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
                        await MessageHandler.delete_message(update)
                        return
                except Exception:
                    pass

                # Если оба API не сработали
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
