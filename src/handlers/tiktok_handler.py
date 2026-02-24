import io
import os
import re
import subprocess
import tempfile
import aiohttp
import logging

from telegram import Update
from utils import delete_message
from . import BaseHandler

logger = logging.getLogger(__name__)

# Regex to extract TikTok URL from message (handles vm., vt., www.tiktok.com)
TIKTOK_URL_PATTERN = re.compile(
    r"https?://(?:vm|vt|www)\.tiktok\.com/[^\s]+",
    re.IGNORECASE
)

USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"


class TikTokHandler(BaseHandler):
    def __init__(self):
        self.TIKTOK_LINKS = ["https://www.tiktok.com/", "https://vm.tiktok.com/", "https://vt.tiktok.com/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.TIKTOK_LINKS)

    def _extract_url(self, message: str) -> str | None:
        """Extract TikTok URL from message (handles extra text around the link)."""
        match = TIKTOK_URL_PATTERN.search(message)
        return match.group(0).rstrip(".,;:!?)") if match else None

    async def _download_via_api(self, url: str) -> bytes | None:
        """Get video URL from tikwm API, download with browser User-Agent, return bytes."""
        try:
            api_url = "https://tikwm.com/api/"
            params = {"url": url}
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, timeout=15) as response:
                    data = await response.json()

            if data.get("code") != 0 or not data.get("data", {}).get("play"):
                logger.debug("tikwm API returned no play URL: %s", data.get("msg", data))
                return None

            video_url = data["data"]["play"]
            headers = {"User-Agent": USER_AGENT, "Referer": "https://www.tiktok.com/"}
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        logger.warning("TikTok CDN returned status %s", resp.status)
                        return None
                    return await resp.read()
        except Exception as e:
            logger.warning("API download failed: %s", e)
            return None

    def _download_via_ytdlp(self, url: str) -> bytes | None:
        """Download video using yt-dlp, return bytes or None."""
        try:
            process = subprocess.run(
                ["yt-dlp", "-o", "-", "--format", "best", url],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if process.stdout and len(process.stdout) > 0:
                return process.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("yt-dlp fallback: %s", e)
        except Exception as e:
            logger.warning("yt-dlp download failed: %s", e)
        return None

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self._extract_url(message)
        if not url:
            logger.warning("No TikTok URL found in message: %s", message[:80])
            return

        tiktok_link = f'<a href="{url}">🎵 TikTok</a>'

        try:
            # 1. Try tikwm API + download (Telegram can't fetch TikTok CDN URLs directly)
            video_bytes = await self._download_via_api(url)
            if video_bytes:
                video_io = io.BytesIO(video_bytes)
                video_io.seek(0)
                await update.message.chat.send_video(
                    video=video_io,
                    caption=self._format_caption(sender_name, tiktok_link),
                    parse_mode="HTML",
                )
                await delete_message(update)
                return

            # 2. Fallback: yt-dlp
            video_bytes = self._download_via_ytdlp(url)
            if video_bytes:
                video_io = io.BytesIO(video_bytes)
                video_io.seek(0)
                await update.message.chat.send_video(
                    video=video_io,
                    caption=self._format_caption(sender_name, tiktok_link),
                    parse_mode="HTML",
                )
                await delete_message(update)
                return

            # 3. Last resort: yt-dlp to temp file (for large videos)
            output_path = None
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "tiktok_video.mp4")
                subprocess.run(
                    ["yt-dlp", "-o", output_path, "--format", "best", url],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as f:
                        await update.message.chat.send_video(
                            video=f,
                            caption=self._format_caption(sender_name, tiktok_link),
                            parse_mode="HTML",
                        )
                    await delete_message(update)
                    return
            except Exception as e:
                logger.warning("yt-dlp temp file fallback failed: %s", e)
            finally:
                if output_path and os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass

        except Exception as e:
            logger.error("TikTok handler failed: %s", e, exc_info=True)
