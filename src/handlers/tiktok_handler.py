import aiohttp
import logging

from telegram import Update
from utils import delete_message
from . import BaseHandler

logger = logging.getLogger(__name__)

class TikTokHandler(BaseHandler):
    def __init__(self):
        self.TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/", "https://vt.tiktok.com/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.TIKTOK_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        tiktok_link = f'<a href="{message}">🎵 TikTok</a>'

        try:
            # Try primary API
            api_url = "https://tikwm.com/api/"
            params = {"url": message}
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, timeout=10) as response:
                    data = await response.json()

            if data.get("code") == 0 and data.get("data", {}).get("play"):
                video_url = data["data"]["play"]
                await update.message.chat.send_video(
                    video=video_url,
                    caption=self._format_caption(sender_name, tiktok_link),
                    parse_mode="HTML"
                )
                await delete_message(update)
                return

            # Try alternative API
            try:
                api_url_alt = "https://api.tiktokdownload.com/api"
                params_alt = {"url": message}
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url_alt, params=params_alt, timeout=15) as response:
                        data_alt = await response.json()

                if data_alt.get("success") and data_alt.get("video_url"):
                    await update.message.chat.send_video(
                        video=data_alt["video_url"],
                        caption=self._format_caption(sender_name, tiktok_link),
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                pass

        except Exception as e:
            pass
