"""Shared, non-blocking download and send helpers used by all handlers."""

import asyncio
import json
import logging
import tempfile
from contextlib import ExitStack
from pathlib import Path

import aiohttp
import yt_dlp
from telegram import InputMediaPhoto, InputMediaVideo, Update

import config
from utils import delete_message

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_GROUP_LIMIT = 10

# Prefer <=1080p, mp4-friendly; fall back to whatever is available.
YTDLP_FORMAT = "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b"

# Caps concurrent downloads so a burst of links doesn't saturate the server.
download_slot = asyncio.Semaphore(config.MAX_PARALLEL_DOWNLOADS)


class DownloadError(Exception):
    pass


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _media_files(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS | PHOTO_EXTENSIONS
    )


def _ytdlp_download(url: str, dest_dir: Path, cookies: Path | None, user_agent: str | None) -> None:
    opts = {
        "outtmpl": str(dest_dir / "%(id)s_%(autonumber)s.%(ext)s"),
        "format": YTDLP_FORMAT,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "logger": logging.getLogger("yt_dlp"),
    }
    if cookies:
        opts["cookiefile"] = str(cookies)
    if user_agent:
        opts["http_headers"] = {"User-Agent": user_agent}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


async def run_ytdlp(
    url: str,
    dest_dir: Path,
    *,
    cookies: Path | None = None,
    user_agent: str | None = None,
) -> list[Path]:
    """Download `url` into `dest_dir` with yt-dlp in a worker thread. Returns media files."""
    try:
        await asyncio.to_thread(_ytdlp_download, url, dest_dir, cookies, user_agent)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadError(str(e)) from e
    files = _media_files(dest_dir)
    if not files:
        raise DownloadError("yt-dlp finished but produced no media files")
    return files


async def download_file(url: str, dest: Path, headers: dict | None = None) -> Path:
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise DownloadError(f"HTTP {resp.status} for {url[:80]}")
            with open(dest, "wb") as f:
                async for chunk in resp.content.iter_chunked(1 << 16):
                    f.write(chunk)
    return dest


async def _run(*cmd: str) -> tuple[int, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("%s failed: %s", cmd[0], stderr.decode(errors="replace")[-500:])
    return proc.returncode, stdout


async def compress_video(path: Path, max_bytes: int = config.MAX_UPLOAD_BYTES) -> Path | None:
    """Re-encode `path` with a bitrate chosen to fit under `max_bytes`."""
    code, out = await _run(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)
    )
    if code != 0:
        return None
    duration = float(json.loads(out)["format"]["duration"])
    audio_kbps = 96
    total_kbps = max_bytes * 8 * 0.9 / duration / 1000
    video_kbps = int(total_kbps - audio_kbps)
    if video_kbps < 150:
        logger.warning("Video too long to fit into the upload limit (%.0fs)", duration)
        return None

    output = path.with_name(f"{path.stem}_compressed.mp4")
    code, _ = await _run(
        "ffmpeg", "-y", "-i", str(path),
        "-vf", "scale='min(720,iw)':-2",
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps * 2}k",
        "-c:a", "aac", "-b:a", f"{audio_kbps}k",
        "-movflags", "+faststart",
        str(output),
    )
    if code != 0 or not output.exists() or output.stat().st_size > max_bytes:
        return None
    return output


async def fit_to_limit(files: list[Path], max_bytes: int = config.MAX_UPLOAD_BYTES) -> list[Path]:
    """Compress oversized videos; drop anything that still doesn't fit."""
    result = []
    for path in files:
        if path.stat().st_size <= max_bytes:
            result.append(path)
            continue
        logger.info("%s is %.1f MB, compressing", path.name, path.stat().st_size / 2**20)
        compressed = await compress_video(path, max_bytes) if is_video(path) else None
        if compressed:
            result.append(compressed)
        else:
            logger.warning("Dropping %s: over the upload limit", path.name)
    return result


async def send_media(update: Update, files: list[Path], caption: str) -> bool:
    """Send one file or an album to the chat, then delete the original message."""
    files = (await fit_to_limit(files))[:MEDIA_GROUP_LIMIT]
    if not files:
        return False

    chat = update.message.chat
    with ExitStack() as stack:
        handles = [stack.enter_context(open(path, "rb")) for path in files]
        if len(files) == 1:
            if is_video(files[0]):
                await chat.send_video(
                    video=handles[0], caption=caption, parse_mode="HTML", supports_streaming=True
                )
            else:
                await chat.send_photo(photo=handles[0], caption=caption, parse_mode="HTML")
        else:
            media = []
            for i, (path, handle) in enumerate(zip(files, handles)):
                extra = {"caption": caption, "parse_mode": "HTML"} if i == 0 else {}
                if is_video(path):
                    media.append(InputMediaVideo(handle, supports_streaming=True, **extra))
                else:
                    media.append(InputMediaPhoto(handle, **extra))
            await chat.send_media_group(media=media)

    await delete_message(update)
    return True


async def download_and_send(update: Update, url: str, caption: str, **ytdlp_kwargs) -> bool:
    """yt-dlp download of `url` followed by send_media, inside a download slot."""
    async with download_slot:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                files = await run_ytdlp(url, Path(tmp), **ytdlp_kwargs)
            except DownloadError as e:
                logger.warning("yt-dlp failed for %s: %s", url, str(e)[-300:])
                return False
            return await send_media(update, files, caption)
