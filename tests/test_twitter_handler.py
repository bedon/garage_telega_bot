import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat

from src.handlers.twitter_handler import TwitterHandler

@pytest.fixture
def twitter_handler():
    return TwitterHandler()

@pytest.mark.asyncio
async def test_can_handle_twitter_links(twitter_handler):
    assert twitter_handler.can_handle("https://twitter.com/user/status/123")
    assert twitter_handler.can_handle("https://x.com/user/status/123")
    assert not twitter_handler.can_handle("https://example.com")

@pytest.mark.asyncio
async def test_handle_twitter_link_success(mock_telegram_update, twitter_handler):
    message = "https://twitter.com/user/status/123"
    sender_name = "Test User"
    
    with patch('subprocess.run') as mock_run:
        # Mock successful video download
        mock_run.return_value.stdout = b"fake video data"
        mock_run.return_value.stderr = b""
        
        await twitter_handler.handle(mock_telegram_update, message, sender_name)
        
        # Verify that send_video was called with correct parameters
        mock_telegram_update.message.chat.send_video.assert_called_once()
        call_args = mock_telegram_update.message.chat.send_video.call_args[1]
        assert "Test User" in call_args['caption']
        assert "From Twitter (X)" in call_args['caption']
        assert call_args['parse_mode'] == "HTML"

@pytest.mark.asyncio
async def test_handle_twitter_link_failure(mock_telegram_update, twitter_handler):
    message = "https://twitter.com/user/status/123"
    sender_name = "Test User"
    
    with patch('subprocess.run') as mock_run:
        # Mock failed video download
        mock_run.side_effect = Exception("Download failed")
        
        await twitter_handler.handle(mock_telegram_update, message, sender_name)
        
        # Verify that send_message was called with fallback message
        mock_telegram_update.message.chat.send_message.assert_called_once()
        # Print the actual call arguments to debug
        print("Call args:", mock_telegram_update.message.chat.send_message.call_args)
        # Access the positional and keyword arguments correctly
        args, kwargs = mock_telegram_update.message.chat.send_message.call_args
        message_text = args[0]  # The message text is the first positional argument
        assert "Test User" in message_text
        assert "Failed to automatically download the video" in message_text
        assert kwargs['parse_mode'] == "HTML" 