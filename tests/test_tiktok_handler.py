import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat
from src.handlers.tiktok_handler import TikTokHandler

@pytest.fixture
def tiktok_handler():
    return TikTokHandler()

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_message = AsyncMock()
    update.message.chat.send_video = AsyncMock()
    return update

@pytest.mark.asyncio
async def test_can_handle_valid_tiktok_links(tiktok_handler):
    assert tiktok_handler.can_handle("https://www.tiktok.com/@user/video/123456789")
    assert tiktok_handler.can_handle("https://vm.tiktok.com/abcdefg/")
    assert not tiktok_handler.can_handle("https://example.com")

@pytest.mark.asyncio
async def test_extract_url_from_message(tiktok_handler):
    assert tiktok_handler._extract_url("check this https://vm.tiktok.com/ZSmCyNC4U/") == "https://vm.tiktok.com/ZSmCyNC4U/"
    assert tiktok_handler._extract_url("https://www.tiktok.com/@user/video/123") == "https://www.tiktok.com/@user/video/123"
    assert tiktok_handler._extract_url("no url here") is None

@pytest.mark.asyncio
async def test_handle_successful_api_download(tiktok_handler, mock_update):
    """Test successful flow when _download_via_api returns video bytes."""
    with patch.object(tiktok_handler, "_download_via_api", new_callable=AsyncMock, return_value=b"fake_video_bytes"):
        with patch.object(tiktok_handler, "_download_via_ytdlp", return_value=None):
            await tiktok_handler.handle(
                mock_update,
                "https://vm.tiktok.com/ZSmCyNC4U/",
                "Test User",
            )

    mock_update.message.chat.send_video.assert_called_once()
    assert "TikTok" in mock_update.message.chat.send_video.call_args[1]["caption"]

@pytest.mark.asyncio
async def test_handle_successful_ytdlp_fallback(tiktok_handler, mock_update):
    """Test yt-dlp fallback when API download fails."""
    with patch.object(tiktok_handler, "_download_via_api", return_value=None):
        with patch.object(tiktok_handler, "_download_via_ytdlp", return_value=b"fake_video"):
            await tiktok_handler.handle(
                mock_update,
                "https://vm.tiktok.com/ZSmCyNC4U/",
                "Test User",
            )

    mock_update.message.chat.send_video.assert_called_once()
    assert "TikTok" in mock_update.message.chat.send_video.call_args[1]["caption"]

@pytest.mark.asyncio
async def test_handle_no_url_in_message(tiktok_handler, mock_update):
    """When no TikTok URL is found, send_video should not be called."""
    await tiktok_handler.handle(mock_update, "just some text", "Test User")
    mock_update.message.chat.send_video.assert_not_called()

@pytest.mark.asyncio
async def test_handle_all_methods_fail(tiktok_handler, mock_update):
    """When all download methods fail, no video is sent (silent failure)."""
    with patch.object(tiktok_handler, "_download_via_api", return_value=None):
        with patch.object(tiktok_handler, "_download_via_ytdlp", return_value=None):
            with patch("subprocess.run", return_value=MagicMock(returncode=1)):
                await tiktok_handler.handle(
                    mock_update,
                    "https://vm.tiktok.com/ZSmCyNC4U/",
                    "Test User",
                )

    mock_update.message.chat.send_video.assert_not_called() 