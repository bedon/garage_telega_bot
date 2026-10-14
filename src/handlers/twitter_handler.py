import logging
import re

from telegram import Update

from downloader import download_and_send
from . import BaseHandler

logger = logging.getLogger(__name__)


class TwitterHandler(BaseHandler):
    URL_PATTERN = re.compile(
        r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/\w+/status/\d+[^\s]*",
        re.IGNORECASE,
    )

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self.extract_url(message)
        caption = self._format_caption(sender_name, url, "🐦 Twitter (X)")
        if not await download_and_send(update, url, caption):
            logger.info("Twitter: nothing sent for %s", url)
