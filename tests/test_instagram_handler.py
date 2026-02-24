import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat
from src.handlers.instagram_handler import InstagramHandler

@pytest.fixture
def instagram_handler():
    return InstagramHandler()

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_message = AsyncMock()
    update.message.chat.send_video = AsyncMock()
    update.message.chat.send_photo = AsyncMock()
    return update

@pytest.mark.asyncio
async def test_can_handle_valid_instagram_links(instagram_handler):
    assert instagram_handler.can_handle("https://www.instagram.com/reel/abc123/")
    assert instagram_handler.can_handle("https://www.instagram.com/p/xyz789/")
    assert not instagram_handler.can_handle("https://example.com")

@pytest.mark.asyncio
async def test_extract_url(instagram_handler):
    assert instagram_handler._extract_url("check this https://www.instagram.com/reel/abc123/") == "https://www.instagram.com/reel/abc123/"
    assert instagram_handler._extract_url("https://www.instagram.com/p/xyz789/") == "https://www.instagram.com/p/xyz789/"
    assert instagram_handler._extract_url("no url here") is None

@pytest.mark.asyncio
async def test_handle_no_url_in_message(instagram_handler, mock_update):
    await instagram_handler.handle(mock_update, "https://www.instagram.com/invalid", "Test User")
    mock_update.message.chat.send_video.assert_not_called()

@pytest.mark.asyncio
async def test_handle_successful_reelsaver_download(instagram_handler, mock_update):
    with patch.object(instagram_handler, "_download_via_reelsaver", new_callable=AsyncMock, return_value=b"fake_video"):
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User",
        )
    mock_update.message.chat.send_video.assert_called_once()
    call_args = mock_update.message.chat.send_video.call_args[1]
    assert "Instagram" in call_args["caption"]
    assert call_args["parse_mode"] == "HTML"

@pytest.mark.asyncio
async def test_handle_all_methods_fail(instagram_handler, mock_update):
    with patch.object(instagram_handler, "_download_via_reelsaver", new_callable=AsyncMock, return_value=None):
        with patch.object(instagram_handler, "yt_dlp_available", False):
            await instagram_handler.handle(
                mock_update,
                "https://www.instagram.com/reel/abc123/",
                "Test User",
            )
    mock_update.message.chat.send_video.assert_not_called() 