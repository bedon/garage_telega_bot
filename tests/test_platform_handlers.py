from unittest.mock import AsyncMock, patch

import pytest

from handlers.facebook_handler import FacebookHandler
from handlers.tiktok_handler import TikTokHandler
from handlers.twitter_handler import TwitterHandler


@pytest.mark.parametrize("handler_cls, message, expected", [
    (TwitterHandler, "lol https://x.com/user/status/123?s=20 nice", "https://x.com/user/status/123?s=20"),
    (TwitterHandler, "https://twitter.com/user/status/1", "https://twitter.com/user/status/1"),
    (FacebookHandler, "see https://www.facebook.com/reel/123/ ok", "https://www.facebook.com/reel/123/"),
    (FacebookHandler, "https://fb.watch/abc/", "https://fb.watch/abc/"),
    (FacebookHandler, "https://www.facebook.com/watch?v=42", "https://www.facebook.com/watch?v=42"),
    (FacebookHandler, "https://www.facebook.com/share/v/AbC/", "https://www.facebook.com/share/v/AbC/"),
    (TikTokHandler, "check https://vm.tiktok.com/ZSmCyNC4U/.", "https://vm.tiktok.com/ZSmCyNC4U/"),
    (TikTokHandler, "https://www.tiktok.com/@user/video/123", "https://www.tiktok.com/@user/video/123"),
])
def test_extract_url(handler_cls, message, expected):
    handler = handler_cls()
    assert handler.can_handle(message)
    assert handler.extract_url(message) == expected


@pytest.mark.parametrize("handler_cls, message", [
    (TwitterHandler, "https://x.com/user"),
    (FacebookHandler, "https://www.facebook.com/someone"),
    (TikTokHandler, "https://example.com/video"),
])
def test_ignores_non_video_links(handler_cls, message):
    assert not handler_cls().can_handle(message)


@pytest.mark.parametrize("handler_cls, module", [
    (TwitterHandler, "handlers.twitter_handler"),
    (FacebookHandler, "handlers.facebook_handler"),
])
async def test_ytdlp_handlers_pass_clean_url(handler_cls, module, mock_update):
    with patch(f"{module}.download_and_send", AsyncMock(return_value=True)) as send:
        await handler_cls().handle(mock_update, "wow https://x.com/u/status/1 https://fb.watch/x/", "by Dude ")
    url, caption = send.call_args.args[1:]
    assert " " not in url
    assert caption.startswith("by Dude from <a href=")


async def test_tiktok_falls_back_to_ytdlp(mock_update):
    handler = TikTokHandler()
    with patch.object(handler, "_download_via_tikwm", AsyncMock(side_effect=Exception("down"))), \
         patch("handlers.tiktok_handler.download_and_send", AsyncMock(return_value=True)) as fallback:
        await handler.handle(mock_update, "https://vm.tiktok.com/abc/", "by Dude ")
    fallback.assert_awaited_once()


async def test_tiktok_uses_tikwm_first(mock_update, tmp_path):
    handler = TikTokHandler()
    video = tmp_path / "t.mp4"
    video.write_bytes(b"v")
    with patch.object(handler, "_download_via_tikwm", AsyncMock(return_value=video)), \
         patch("handlers.tiktok_handler.download_and_send", AsyncMock()) as fallback:
        await handler.handle(mock_update, "https://vm.tiktok.com/abc/", "by Dude ")
    mock_update.message.chat.send_video.assert_awaited_once()
    fallback.assert_not_called()
