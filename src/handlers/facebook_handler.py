import logging
import re

from telegram import Update

from downloader import download_and_send
from . import BaseHandler

logger = logging.getLogger(__name__)


class FacebookHandler(BaseHandler):
    URL_PATTERN = re.compile(
        r"https?://(?:(?:www|m|web)\.)?"
        r"(?:facebook\.com/(?:reel/|watch/?\?|share/[rv]/|[\w.]+/videos/)|fb\.watch/)[^\s]+",
        re.IGNORECASE,
    )

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self.extract_url(message)
        caption = self._format_caption(sender_name, url, "📘 Facebook")
        if not await download_and_send(update, url, caption):
            logger.info("Facebook: nothing sent for %s", url)
