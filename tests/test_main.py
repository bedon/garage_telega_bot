from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Message, Update, User

import main


def make_update(text):
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = text
    update.message.from_user = MagicMock(spec=User, id=1, full_name="Test User")
    update.message.chat_id = 123
    return update


async def test_handler_ignores_updates_without_message():
    update = MagicMock(spec=Update)
    update.message = None
    await main.handler(update, MagicMock())


async def test_handler_ignores_messages_without_text():
    await main.handler(make_update(None), MagicMock())


async def test_handler_dispatches_to_first_matching_handler():
    first, second = MagicMock(), MagicMock()
    first.can_handle.return_value = True
    first.handle = AsyncMock()
    second.handle = AsyncMock()
    with patch.object(main, "all_handlers", [first, second]):
        await main.handler(make_update("https://x.com/a/status/1"), MagicMock())
    first.handle.assert_awaited_once()
    assert first.handle.call_args.args[1] == "https://x.com/a/status/1"
    second.handle.assert_not_called()


async def test_handler_swallows_handler_exceptions():
    failing = MagicMock()
    failing.can_handle.return_value = True
    failing.handle = AsyncMock(side_effect=Exception("boom"))
    with patch.object(main, "all_handlers", [failing]):
        await main.handler(make_update("link"), MagicMock())


def test_main_requires_token(monkeypatch):
    monkeypatch.setattr(main.config, "TELEGRAM_TOKEN", None)
    with pytest.raises(ValueError):
        main.main()


def test_main_builds_and_polls(monkeypatch):
    monkeypatch.setattr(main.config, "TELEGRAM_TOKEN", "123:abc")
    with patch.object(main, "ApplicationBuilder") as builder:
        main.main()
    app = builder.return_value.token.return_value.concurrent_updates.return_value \
        .media_write_timeout.return_value.build.return_value
    app.add_handler.assert_called_once()
    app.run_polling.assert_called_once()
