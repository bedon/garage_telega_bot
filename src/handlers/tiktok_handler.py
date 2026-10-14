import logging
import re
import tempfile
from pathlib import Path

import aiohttp
from telegram import Update

import config
from downloader import DownloadError, download_and_send, download_file, download_slot, send_media
from . import BaseHandler

logger = logging.getLogger(__name__)

TIKWM_API = "https://tikwm.com/api/"


class TikTokHandler(BaseHandler):
    URL_PATTERN = re.compile(r"https?://(?:(?:vm|vt|www|m)\.)?tiktok\.com/[^\s]+", re.IGNORECASE)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self.extract_url(message)
        caption = self._format_caption(sender_name, url, "🎵 TikTok")

        # 1. tikwm API: fast and watermark-free.
        async with download_slot:
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    video = await self._download_via_tikwm(url, Path(tmp))
                    if await send_media(update, [video], caption):
                        return
                except Exception as e:
                    logger.warning("TikTok: tikwm failed: %s", e)

        # 2. Fallback: yt-dlp.
        if not await download_and_send(update, url, caption):
            logger.warning("TikTok: all download methods failed for %s", url)

    async def _download_via_tikwm(self, url: str, dest: Path) -> Path:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(TIKWM_API, params={"url": url}) as resp:
                data = await resp.json(content_type=None)
        play_url = (data.get("data") or {}).get("play")
        if data.get("code") != 0 or not play_url:
            raise DownloadError(f"tikwm: {data.get('msg', data)}")
        headers = {"User-Agent": config.DEFAULT_USER_AGENT, "Referer": "https://www.tiktok.com/"}
        return await download_file(play_url, dest / "tiktok.mp4", headers)
