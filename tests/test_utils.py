from unittest.mock import AsyncMock, MagicMock

from telegram import Message, Update, User

from utils import delete_message, load_handlers, randomize_status

STATUSES = ["👑 NICE GUY 👑", "😎 CHILL GUY 🚬", "COOL DUDE 🤘", "FUNNY DUDE 🤣"]
SPAMMER = "🌈 GAY SPAMMER 💦💦💦\n"


def make_user(user_id, name="Test User"):
    user = MagicMock(spec=User)
    user.id = user_id
    user.full_name = name
    return user


async def test_delete_message_success():
    update = MagicMock(spec=Update)
    update.message = AsyncMock(spec=Message)
    await delete_message(update)
    update.message.delete.assert_called_once()


async def test_delete_message_failure_is_swallowed():
    update = MagicMock(spec=Update)
    update.message = AsyncMock(spec=Message)
    update.message.delete.side_effect = Exception("Delete failed")
    await delete_message(update)
    update.message.delete.assert_called_once()


async def test_randomize_status_new_user():
    user = make_user(123)
    result = await randomize_status(user, 123)
    assert "Test User" in result
    assert "tg://user?id=123" in result
    assert any(status in result for status in STATUSES)


async def test_randomize_status_streak():
    user = make_user(456)
    assert SPAMMER not in await randomize_status(user, 456)
    assert SPAMMER not in await randomize_status(user, 456)
    assert SPAMMER in await randomize_status(user, 456)


async def test_randomize_status_different_users_reset_streak():
    await randomize_status(make_user(1, "User1"), 789)
    result = await randomize_status(make_user(2, "User2"), 789)
    assert "User2" in result
    assert SPAMMER not in result


async def test_randomize_status_escapes_html_in_name():
    result = await randomize_status(make_user(999, "<b>Bad & Co</b>"), 999)
    assert "&lt;b&gt;Bad &amp; Co&lt;/b&gt;" in result


def test_load_handlers_finds_each_platform_once():
    names = sorted(type(h).__name__ for h in load_handlers())
    assert names == ["FacebookHandler", "InstagramHandler", "TikTokHandler", "TwitterHandler"]
