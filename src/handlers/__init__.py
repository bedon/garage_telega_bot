from abc import ABC, abstractmethod

class BaseHandler(ABC):
    def _format_caption(self, sender_name: str, link: str) -> str:
        return f"{sender_name}from {link}"

    @abstractmethod
    def can_handle(self, message: str) -> bool:
        pass

    @abstractmethod
    async def handle(self, update, message: str, sender_name: str) -> None:
        pass
