import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat
from src.handlers.facebook_handler import FacebookHandler

@pytest.fixture
def facebook_handler():
    return FacebookHandler()

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_message = AsyncMock()
    update.message.chat.send_video = AsyncMock()
    return update

@pytest.mark.asyncio
async def test_can_handle_valid_facebook_links(facebook_handler):
    assert facebook_handler.can_handle("https://www.facebook.com/reel/123456789")
    assert facebook_handler.can_handle("https://fb.watch/abcdefg")
    assert not facebook_handler.can_handle("https://example.com")

@pytest.mark.asyncio
async def test_handle_successful_memory_download(facebook_handler, mock_update):
    with patch('subprocess.run') as mock_run:
        # Mock successful yt-dlp output to memory
        mock_run.return_value.stdout = b"fake video data"
        mock_run.return_value.returncode = 0
        
        await facebook_handler.handle(
            mock_update,
            "https://www.facebook.com/reel/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "From Facebook" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_successful_file_download(facebook_handler, mock_update):
    with patch('subprocess.run') as mock_run, \
         patch('os.path.exists') as mock_exists, \
         patch('os.path.getsize') as mock_size, \
         patch('builtins.open', new_callable=MagicMock) as mock_open:
        # Mock failed memory download
        mock_run.return_value.stdout = b""
        mock_run.return_value.returncode = 1
        
        # Mock successful file download
        mock_exists.return_value = True
        mock_size.return_value = 1000
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        await facebook_handler.handle(
            mock_update,
            "https://www.facebook.com/reel/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "From Facebook" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_download_failure(facebook_handler, mock_update):
    with patch('subprocess.run') as mock_run, \
         patch('os.path.exists') as mock_exists:
        # Mock failed memory download
        mock_run.return_value.stdout = b""
        mock_run.return_value.returncode = 1
        
        # Mock failed file download
        mock_exists.return_value = False
        
        await facebook_handler.handle(
            mock_update,
            "https://www.facebook.com/reel/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0]
        assert "fdown.net" in mock_update.message.chat.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_exception_handling(facebook_handler, mock_update):
    with patch('subprocess.run', side_effect=Exception("Test error")):
        await facebook_handler.handle(
            mock_update,
            "https://www.facebook.com/reel/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0]
        assert "fdown.net" in mock_update.message.chat.send_message.call_args[0][0]
        assert "snapvid.net" in mock_update.message.chat.send_message.call_args[0][0] 