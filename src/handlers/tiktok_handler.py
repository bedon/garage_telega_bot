import requests
from telegram import Update

from utils import delete_message


class TikTokHandler:
    def __init__(self):
        self.TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.TIKTOK_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
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
                # Try alternative API
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
                    pass

                # If both APIs failed
                await update.message.chat.send_message(
                    f"{sender_name} {tiktok_link}\n\n[Failed to get video]",
                    parse_mode="HTML"
                )

        except Exception as e:
            print(f"Error processing TikTok video: {e}")
            await update.message.chat.send_message(
                f"{sender_name} {tiktok_link}\n\n[Error downloading video]",
                parse_mode="HTML"
            )
