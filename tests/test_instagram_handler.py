import logging
import os
from unittest.mock import AsyncMock, patch

import pytest

import instagram_session
from tests.conftest import make_file
from handlers.instagram_handler import InstagramHandler


@pytest.fixture
def handler():
    return InstagramHandler()


@pytest.fixture
def logged_in():
    instagram_session.save_session({"sessionid": "s", "csrftoken": "c"}, "UA")


def patch_methods(handler, ytdlp=None, insta=None, reelsaver=None):
    """Patch the three download methods; each value is a list of files or an Exception."""
    calls = []

    def fake(name, result):
        async def method(*args):
            calls.append(name)
            if isinstance(result, Exception):
                raise result
            return result or []
        return method

    return calls, [
        patch.object(handler, "_via_ytdlp", fake("yt-dlp", ytdlp)),
        patch.object(handler, "_via_instaloader", fake("instaloader", insta)),
        patch.object(handler, "_via_reelsaver", fake("reelsaver", reelsaver)),
    ]


async def run_download(handler, url, tmp_path, **results):
    calls, patches = patch_methods(handler, **results)
    for p in patches:
        p.start()
    try:
        files = await handler._download(url, tmp_path)
    finally:
        for p in patches:
            p.stop()
    return calls, files


@pytest.mark.parametrize("message, expected", [
    ("https://www.instagram.com/reel/abc123/", "https://www.instagram.com/reel/abc123/"),
    ("look https://instagram.com/reels/abc123/?igsh=x!", "https://instagram.com/reels/abc123/?igsh=x"),
    ("https://www.instagram.com/p/xyz_-9/", "https://www.instagram.com/p/xyz_-9/"),
    ("https://www.instagram.com/someone/p/xyz/", "https://www.instagram.com/someone/p/xyz/"),
    ("https://www.instagram.com/tv/tv1/", "https://www.instagram.com/tv/tv1/"),
    ("https://www.instagram.com/share/reel/BA1/", "https://www.instagram.com/share/reel/BA1/"),
])
def test_extract_url(handler, message, expected):
    assert handler.can_handle(message)
    assert handler.extract_url(message) == expected


def test_ignores_profiles_and_other_sites(handler):
    assert not handler.can_handle("https://www.instagram.com/someone/")
    assert not handler.can_handle("https://example.com/reel/abc")


async def test_reel_without_session_skips_instaloader(handler, tmp_path):
    calls, files = await run_download(
        handler, "https://www.instagram.com/reel/abc/", tmp_path,
        ytdlp=Exception("nope"), reelsaver=[tmp_path / "r.mp4"],
    )
    assert calls == ["yt-dlp", "reelsaver"]
    assert files == [tmp_path / "r.mp4"]


async def test_reel_with_session_tries_ytdlp_first(handler, tmp_path, logged_in):
    calls, _ = await run_download(
        handler, "https://www.instagram.com/reel/abc/", tmp_path,
        ytdlp=Exception("a"), insta=Exception("b"), reelsaver=Exception("c"),
    )
    assert calls == ["yt-dlp", "instaloader", "reelsaver"]


async def test_post_with_session_tries_instaloader_first(handler, tmp_path, logged_in):
    calls, files = await run_download(
        handler, "https://www.instagram.com/p/abc/", tmp_path, insta=[tmp_path / "01.jpg"],
    )
    assert calls == ["instaloader"]
    assert files == [tmp_path / "01.jpg"]


async def test_ytdlp_receives_canonical_url_and_cookies(handler, tmp_path, logged_in):
    with patch.object(handler, "_via_ytdlp", AsyncMock(return_value=["f"])) as ytdlp:
        await handler._download("https://www.instagram.com/reels/abc/?igsh=x", tmp_path)
    url, _, cookies = ytdlp.call_args.args
    assert url == "https://www.instagram.com/reel/abc/"
    assert cookies == instagram_session.cookies_file()


async def test_expired_session_is_logged(handler, tmp_path, logged_in, caplog):
    with caplog.at_level(logging.ERROR):
        await run_download(
            handler, "https://www.instagram.com/reel/abc/", tmp_path,
            ytdlp=Exception("ERROR: login required"), insta=Exception("401 Unauthorized"),
            reelsaver=Exception("down"),
        )
    assert "make ig-login" in caplog.text
    assert "expired" in caplog.text


async def test_handle_sends_media_with_caption(handler, mock_update, tmp_path):
    video = make_file(tmp_path, "v.mp4")
    with patch.object(handler, "_download", AsyncMock(return_value=[video])):
        await handler.handle(mock_update, "https://www.instagram.com/reel/abc/?a=1&b=2", "by Dude ")
    caption = mock_update.message.chat.send_video.call_args.kwargs["caption"]
    assert caption == 'by Dude from <a href="https://www.instagram.com/reel/abc/?a=1&amp;b=2">📸 Instagram</a>'
    mock_update.message.delete.assert_awaited_once()


async def test_handle_all_methods_fail(handler, mock_update):
    with patch.object(handler, "_download", AsyncMock(return_value=[])):
        await handler.handle(mock_update, "https://www.instagram.com/reel/abc/", "by Dude ")
    mock_update.message.chat.send_video.assert_not_called()
    mock_update.message.delete.assert_not_called()


async def test_loader_requires_logged_in_cookies(handler):
    instagram_session.save_session({"mid": "x"}, "UA")
    with pytest.raises(Exception, match="not logged in"):
        handler._get_loader()


async def test_loader_reloads_when_cookies_change(handler, logged_in):
    first = handler._get_loader()
    assert handler._get_loader() is first
    cookies = instagram_session.cookies_file()
    os.utime(cookies, (1, 1))
    assert handler._get_loader() is not first
