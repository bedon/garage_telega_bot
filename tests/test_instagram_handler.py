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
async def test_handle_invalid_link(instagram_handler, mock_update):
    invalid_link = "https://www.instagram.com/invalid"
    await instagram_handler.handle(mock_update, invalid_link, "Test User")
    
    mock_update.message.chat.send_message.assert_called_once()
    assert "Invalid Instagram link" in mock_update.message.chat.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_successful_video_download(instagram_handler, mock_update):
    with patch('subprocess.run') as mock_run:
        # Mock successful yt-dlp output
        mock_run.return_value.stdout = b"fake video data"
        mock_run.return_value.returncode = 0
        
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "From Instagram" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_fallback_to_api(instagram_handler, mock_update):
    with patch('subprocess.run') as mock_run, \
         patch('requests.get') as mock_get:
        # Mock failed yt-dlp
        mock_run.return_value.stdout = b""
        mock_run.return_value.returncode = 1
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": None,
            "download_url": "https://example.com/video.mp4",
            "media_type": "video"
        }
        mock_get.return_value = mock_response
        
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "From Instagram" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_all_methods_fail(instagram_handler, mock_update):
    with patch('subprocess.run') as mock_run, \
         patch('requests.get') as mock_get:
        # Mock all methods failing
        mock_run.return_value.stdout = b""
        mock_run.return_value.returncode = 1
        mock_get.return_value.status_code = 500
        
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_exception_handling(instagram_handler, mock_update):
    with patch('subprocess.run', side_effect=Exception("Test error")):
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0]
        assert "Try these services" in mock_update.message.chat.send_message.call_args[0][0] 