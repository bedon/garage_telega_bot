import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes
from src.main import handler, main

@pytest.mark.asyncio
async def test_handler_no_message():
    # Test when update has no message
    mock_update = MagicMock(spec=Update)
    mock_update.message = None
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await handler(mock_update, mock_context)
    # Should return without doing anything

@pytest.mark.asyncio
async def test_handler_no_text():
    # Test when message has no text
    mock_message = MagicMock(spec=Message)
    mock_message.text = None
    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    await handler(mock_update, mock_context)
    # Should return without doing anything

@pytest.mark.asyncio
async def test_handler_success():
    # Test successful message handling
    mock_message = MagicMock(spec=Message)
    mock_message.text = "test message"
    mock_message.from_user = MagicMock(spec=User)
    mock_message.from_user.full_name = "Test User"
    mock_message.chat_id = 123
    
    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock the handlers
    mock_handler = MagicMock()
    mock_handler.can_handle.return_value = True
    mock_handler.handle = AsyncMock()
    
    with patch('src.main.all_handlers', [mock_handler]):
        await handler(mock_update, mock_context)
        
        # Verify handler was called
        mock_handler.can_handle.assert_called_once_with("test message")
        mock_handler.handle.assert_called_once()

@pytest.mark.asyncio
async def test_handler_exception():
    # Test exception handling
    mock_message = MagicMock(spec=Message)
    mock_message.text = "test message"
    mock_message.from_user = MagicMock(spec=User)
    mock_message.from_user.full_name = "Test User"
    mock_message.chat_id = 123
    
    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Mock a handler that raises an exception
    mock_handler = MagicMock()
    mock_handler.can_handle.return_value = True
    mock_handler.handle = AsyncMock(side_effect=Exception("Test error"))
    
    with patch('src.main.all_handlers', [mock_handler]):
        # Should not raise an exception
        await handler(mock_update, mock_context)

def test_main():
    # Test the main function
    with patch('src.main.ApplicationBuilder') as mock_builder:
        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        
        main()
        
        # Verify the application was built and started
        mock_builder.return_value.token.assert_called_once()
        mock_app.add_handler.assert_called_once()
        mock_app.run_polling.assert_called_once() 