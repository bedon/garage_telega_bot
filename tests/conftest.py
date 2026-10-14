from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update

import config


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.delete = AsyncMock()
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.send_message = AsyncMock()
    update.message.chat.send_video = AsyncMock()
    update.message.chat.send_photo = AsyncMock()
    update.message.chat.send_media_group = AsyncMock()
    return update


@pytest.fixture(autouse=True)
def instagram_data_dir(tmp_path, monkeypatch):
    """Point the Instagram session files at an empty temp dir for every test."""
    data_dir = tmp_path / "instagram"
    monkeypatch.setattr(config, "INSTAGRAM_DATA_DIR", data_dir)
    monkeypatch.setattr(config, "INSTAGRAM_COOKIES_FILE", data_dir / "cookies.txt")
    monkeypatch.setattr(config, "INSTAGRAM_USER_AGENT_FILE", data_dir / "user_agent.txt")
    return data_dir


def make_file(directory, name, size=10):
    path = directory / name
    path.write_bytes(b"x" * size)
    return path
