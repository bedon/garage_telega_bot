import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message, User, Chat
from src.utils import delete_message, randomize_status, load_handlers

@pytest.mark.asyncio
async def test_delete_message_success():
    # Create a mock update with a message
    mock_message = AsyncMock(spec=Message)
    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    
    # Call the function
    await delete_message(mock_update)
    
    # Verify the message was deleted
    mock_message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_delete_message_failure():
    # Create a mock update with a message that raises an exception
    mock_message = AsyncMock(spec=Message)
    mock_message.delete.side_effect = Exception("Delete failed")
    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    
    # Call the function - should not raise an exception
    await delete_message(mock_update)
    
    # Verify the message delete was attempted
    mock_message.delete.assert_called_once()

@pytest.mark.asyncio
async def test_randomize_status_new_user():
    # Test with a new user
    user_name = "Test User"
    chat_id = 123
    
    result = await randomize_status(user_name, chat_id)
    
    # Check that the result contains the user name
    assert user_name in result
    # Check that it starts with a status
    assert result.startswith(("👑 NICE GUY 👑\n", "😎 CHILL GUY 🚬\n", "COOL DUDE 🤘\n", "FUNNY DUDE 🤣\n"))

@pytest.mark.asyncio
async def test_randomize_status_streak():
    # Test streak functionality
    user_name = "Test User"
    chat_id = 456
    
    # First message
    result1 = await randomize_status(user_name, chat_id)
    assert "🌈 GAY SPAMMER 💦💦💦\n" not in result1
    
    # Second message from same user
    result2 = await randomize_status(user_name, chat_id)
    assert "🌈 GAY SPAMMER 💦💦💦\n" not in result2
    
    # Third message from same user
    result3 = await randomize_status(user_name, chat_id)
    assert "🌈 GAY SPAMMER 💦💦💦\n" in result3

@pytest.mark.asyncio
async def test_randomize_status_different_users():
    # Test with different users
    chat_id = 789
    
    # First user
    result1 = await randomize_status("User1", chat_id)
    
    # Second user
    result2 = await randomize_status("User2", chat_id)
    
    assert "User1" in result1
    assert "User2" in result2
    assert "🌈 GAY SPAMMER 💦💦💦\n" not in result2

def test_load_handlers():
    # Test that load_handlers returns a list
    handlers = load_handlers()
    
    # Check that we got a list
    assert isinstance(handlers, list)
    
    # Check that all items in the list are handler instances
    for handler in handlers:
        assert hasattr(handler, 'can_handle')
        assert hasattr(handler, 'handle') 