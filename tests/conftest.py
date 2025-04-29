import pytest
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, Message, Chat
import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

@pytest.fixture
def mock_telegram_update():
    """Create a mock Telegram Update object."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_video = AsyncMock()
    update.message.chat.send_message = AsyncMock()
    return update 