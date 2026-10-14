from unittest.mock import patch

import pytest
from telegram import InputMediaPhoto, InputMediaVideo

import downloader
from tests.conftest import make_file


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL; records options and writes one file."""
    last_opts = None

    def __init__(self, opts):
        FakeYDL.last_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def download(self, urls):
        out = self.last_opts["outtmpl"].replace("%(id)s_%(autonumber)s.%(ext)s", "vid_1.mp4")
        with open(out, "wb") as f:
            f.write(b"video")


async def test_run_ytdlp_passes_cookies_and_user_agent(tmp_path):
    cookies = make_file(tmp_path, "cookies.txt")
    with patch.object(downloader.yt_dlp, "YoutubeDL", FakeYDL):
        files = await downloader.run_ytdlp(
            "https://example.com/v", tmp_path, cookies=cookies, user_agent="UA/1.0"
        )
    assert [f.name for f in files] == ["vid_1.mp4"]
    assert FakeYDL.last_opts["cookiefile"] == str(cookies)
    assert FakeYDL.last_opts["http_headers"] == {"User-Agent": "UA/1.0"}


async def test_run_ytdlp_wraps_errors(tmp_path):
    class FailingYDL(FakeYDL):
        def download(self, urls):
            raise downloader.yt_dlp.utils.DownloadError("ERROR: login required")

    with patch.object(downloader.yt_dlp, "YoutubeDL", FailingYDL):
        with pytest.raises(downloader.DownloadError, match="login required"):
            await downloader.run_ytdlp("https://example.com/v", tmp_path)


async def test_run_ytdlp_without_output_raises(tmp_path):
    class EmptyYDL(FakeYDL):
        def download(self, urls):
            pass

    with patch.object(downloader.yt_dlp, "YoutubeDL", EmptyYDL):
        with pytest.raises(downloader.DownloadError):
            await downloader.run_ytdlp("https://example.com/v", tmp_path)


async def test_send_media_single_video(tmp_path, mock_update):
    video = make_file(tmp_path, "a.mp4")
    assert await downloader.send_media(mock_update, [video], "cap")
    kwargs = mock_update.message.chat.send_video.call_args.kwargs
    assert kwargs["caption"] == "cap"
    assert kwargs["parse_mode"] == "HTML"
    mock_update.message.delete.assert_awaited_once()


async def test_send_media_single_photo(tmp_path, mock_update):
    photo = make_file(tmp_path, "a.jpg")
    assert await downloader.send_media(mock_update, [photo], "cap")
    mock_update.message.chat.send_photo.assert_awaited_once()
    mock_update.message.chat.send_video.assert_not_called()


async def test_send_media_album_puts_caption_on_first_item(tmp_path, mock_update):
    files = [make_file(tmp_path, "01.jpg"), make_file(tmp_path, "02.mp4")]
    assert await downloader.send_media(mock_update, files, "cap")
    media = mock_update.message.chat.send_media_group.call_args.kwargs["media"]
    assert isinstance(media[0], InputMediaPhoto) and media[0].caption == "cap"
    assert isinstance(media[1], InputMediaVideo) and media[1].caption is None


async def test_send_media_caps_album_at_ten(tmp_path, mock_update):
    files = [make_file(tmp_path, f"{i:02d}.jpg") for i in range(12)]
    await downloader.send_media(mock_update, files, "cap")
    assert len(mock_update.message.chat.send_media_group.call_args.kwargs["media"]) == 10


async def test_send_media_returns_false_when_nothing_fits(tmp_path, mock_update):
    video = make_file(tmp_path, "a.mp4")
    with patch.object(downloader, "fit_to_limit", return_value=[]):
        assert not await downloader.send_media(mock_update, [video], "cap")
    mock_update.message.delete.assert_not_called()


async def test_fit_to_limit_drops_oversized_photo(tmp_path):
    big_photo = make_file(tmp_path, "a.jpg", size=100)
    with patch.object(downloader, "compress_video") as compress:
        assert await downloader.fit_to_limit([big_photo], max_bytes=50) == []
    compress.assert_not_called()


async def test_fit_to_limit_compresses_large_video(tmp_path):
    big = make_file(tmp_path, "big.mp4", size=100)
    small = make_file(tmp_path, "small.mp4", size=10)
    with patch.object(downloader, "compress_video", return_value=small) as compress:
        assert await downloader.fit_to_limit([big], max_bytes=50) == [small]
    compress.assert_awaited_once()
