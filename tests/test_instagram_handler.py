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
    # Create a mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "error": None,
        "download_url": "https://example.com/video.mp4",
        "media_type": "video"
    })
    
    # Create a mock session with proper async context manager support
    mock_session = MagicMock()
    mock_session.get = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None
    
    # Create a mock session context manager
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    # Patch the ClientSession to return our mock session context
    with patch('aiohttp.ClientSession', return_value=mock_session_context):
        # Call the handler with a valid Instagram link
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        # Debug prints
        print("Send video called:", mock_update.message.chat.send_video.called)
        print("Send video call count:", mock_update.message.chat.send_video.call_count)
        if mock_update.message.chat.send_video.called:
            print("Send video call args:", mock_update.message.chat.send_video.call_args)
        
        # Verify that send_video was called with the correct arguments
        mock_update.message.chat.send_video.assert_called_once()
        call_args = mock_update.message.chat.send_video.call_args[1]
        assert call_args['video'] == "https://example.com/video.mp4"
        assert "Instagram" in call_args['caption']
        assert call_args['parse_mode'] == "HTML"

@pytest.mark.asyncio
async def test_handle_fallback_to_api(instagram_handler, mock_update):
    # Mock failed API response
    mock_api_response = AsyncMock()
    mock_api_response.status = 500
    mock_api_response.json = AsyncMock(return_value={"error": "API error"})
    
    # Mock successful HTML response
    mock_html_response = AsyncMock()
    mock_html_response.status = 200
    mock_html_response.text = AsyncMock(return_value='video_url":"https://example.com/video.mp4"')
    
    mock_context1 = AsyncMock()
    mock_context1.__aenter__.return_value = mock_api_response
    mock_context1.__aexit__.return_value = None
    
    mock_context2 = AsyncMock()
    mock_context2.__aenter__.return_value = mock_html_response
    mock_context2.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.get.side_effect = [mock_context1, mock_context2]
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "Instagram" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_all_methods_fail(instagram_handler, mock_update):
    mock_response = AsyncMock()
    mock_response.status = 500
    
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_context.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_context
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_exception_handling(instagram_handler, mock_update):
    with patch('aiohttp.ClientSession', side_effect=Exception("Test error")):
        await instagram_handler.handle(
            mock_update,
            "https://www.instagram.com/reel/abc123/",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "Failed to automatically download" in mock_update.message.chat.send_message.call_args[0][0] 