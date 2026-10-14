import html
import re
from abc import ABC, abstractmethod

TRAILING_PUNCTUATION = ".,;:!?)>]\"'"


class BaseHandler(ABC):
    # Regex that matches a supported URL inside a message.
    URL_PATTERN: re.Pattern

    def can_handle(self, message: str) -> bool:
        return self.URL_PATTERN.search(message) is not None

    def extract_url(self, message: str) -> str | None:
        match = self.URL_PATTERN.search(message)
        return match.group(0).rstrip(TRAILING_PUNCTUATION) if match else None

    def _format_caption(self, sender_name: str, url: str, label: str) -> str:
        return f'{sender_name}from <a href="{html.escape(url)}">{label}</a>'

    @abstractmethod
    async def handle(self, update, message: str, sender_name: str) -> None:
        pass
