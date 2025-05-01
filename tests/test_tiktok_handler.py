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
async def test_handle_successful_first_api(tiktok_handler, mock_update):
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "code": 0,
        "data": {
            "play": "https://example.com/video.mp4"
        }
    })
    
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_context.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_context
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await tiktok_handler.handle(
            mock_update,
            "https://www.tiktok.com/@user/video/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "TikTok" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_successful_second_api(tiktok_handler, mock_update):
    # Mock failed response from first API
    mock_response1 = AsyncMock()
    mock_response1.json = AsyncMock(return_value={"code": 1})
    
    # Mock successful response from second API
    mock_response2 = AsyncMock()
    mock_response2.json = AsyncMock(return_value={
        "success": True,
        "video_url": "https://example.com/video.mp4"
    })
    
    mock_context1 = AsyncMock()
    mock_context1.__aenter__.return_value = mock_response1
    mock_context1.__aexit__.return_value = None
    
    mock_context2 = AsyncMock()
    mock_context2.__aenter__.return_value = mock_response2
    mock_context2.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.get.side_effect = [mock_context1, mock_context2]
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await tiktok_handler.handle(
            mock_update,
            "https://www.tiktok.com/@user/video/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_video.assert_called_once()
        assert "TikTok" in mock_update.message.chat.send_video.call_args[1]['caption']

@pytest.mark.asyncio
async def test_handle_both_apis_fail(tiktok_handler, mock_update):
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"code": 1})
    
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_context.__aexit__.return_value = None
    
    mock_session = AsyncMock()
    mock_session.get.return_value = mock_context
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await tiktok_handler.handle(
            mock_update,
            "https://www.tiktok.com/@user/video/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "[Error downloading video]" in mock_update.message.chat.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_exception_handling(tiktok_handler, mock_update):
    with patch('aiohttp.ClientSession', side_effect=Exception("Test error")):
        await tiktok_handler.handle(
            mock_update,
            "https://www.tiktok.com/@user/video/123456789",
            "Test User"
        )
        
        mock_update.message.chat.send_message.assert_called_once()
        assert "[Error downloading video]" in mock_update.message.chat.send_message.call_args[0][0] 