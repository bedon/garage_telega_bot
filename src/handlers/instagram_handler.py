import asyncio
import logging
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import aiohttp
import instaloader
from telegram import Update

import config
import instagram_session
from downloader import DownloadError, download_file, download_slot, run_ytdlp, send_media
from . import BaseHandler

logger = logging.getLogger(__name__)

REELSAVER_API = "https://reelsaver.vercel.app/api/video"

# Errors that mean the session is missing, expired or flagged by Instagram.
SESSION_ERROR_MARKERS = (
    "login required",
    "log in",
    "logged in",
    "401",
    "checkpoint",
    "challenge_required",
    "please wait a few minutes",
    "rate-limit",
)

SHORTCODE_PATTERN = re.compile(r"/(p|reels?|tv)/([\w-]+)")


class InstagramHandler(BaseHandler):
    URL_PATTERN = re.compile(
        r"https?://(?:www\.|m\.)?instagram\.com/(?:[\w.]+/)?(?:p|reels?|tv|share)/[^\s]+",
        re.IGNORECASE,
    )

    def __init__(self):
        self._loader: instaloader.Instaloader | None = None
        self._loader_mtime: float | None = None

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self.extract_url(message)
        if not url:
            return

        caption = self._format_caption(sender_name, url, "📸 Instagram")
        logger.info("Instagram: processing %s", url)

        async with download_slot:
            with tempfile.TemporaryDirectory() as tmp:
                files = await self._download(url, Path(tmp))
                if files and await send_media(update, files, caption):
                    return
        logger.warning("Instagram: all download methods failed for %s", url)

    async def _download(self, url: str, tmp: Path) -> list[Path]:
        url = await self._resolve_share_link(url)
        match = SHORTCODE_PATTERN.search(url)
        if not match:
            logger.warning("Instagram: can't find a shortcode in %s", url)
            return []
        kind, shortcode = match.groups()
        kind = "reel" if kind.startswith("reel") else kind
        canonical = f"https://www.instagram.com/{kind}/{shortcode}/"

        cookies = instagram_session.cookies_file()
        methods = [
            ("yt-dlp", lambda d: self._via_ytdlp(canonical, d, cookies)),
            ("instaloader", lambda d: self._via_instaloader(shortcode, d)),
            ("reelsaver", lambda d: self._via_reelsaver(canonical, d)),
        ]
        if not cookies:
            # Anonymous instaloader is blocked almost everywhere; don't burn requests on it.
            methods = [m for m in methods if m[0] != "instaloader"]
        elif kind == "p":
            # Posts may be photos/carousels, which only instaloader handles fully.
            methods.insert(0, methods.pop(1))

        session_problem = False
        for name, method in methods:
            dest = tmp / name
            dest.mkdir()
            try:
                files = await method(dest)
                if files:
                    logger.info("Instagram: %s succeeded (%d file(s))", name, len(files))
                    return files
            except Exception as e:
                error = str(e)
                logger.warning("Instagram: %s failed: %s", name, error[-300:])
                session_problem |= any(m in error.lower() for m in SESSION_ERROR_MARKERS)

        if session_problem:
            if cookies:
                logger.error(
                    "Instagram session looks expired or flagged. "
                    "Run `make ig-login` on the server to refresh it."
                )
            else:
                logger.error(
                    "Instagram requires login for this post. "
                    "Run `make ig-login` on the server to create a session."
                )
        return []

    async def _resolve_share_link(self, url: str) -> str:
        """`/share/...` links redirect to the real post URL."""
        if "/share/" not in url:
            return url
        headers = {"User-Agent": instagram_session.user_agent()}
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    return str(resp.url)
        except Exception as e:
            logger.warning("Instagram: failed to resolve share link: %s", e)
            return url

    async def _via_ytdlp(self, url: str, dest: Path, cookies: Path | None) -> list[Path]:
        return await run_ytdlp(
            url, dest, cookies=cookies, user_agent=instagram_session.user_agent()
        )

    def _get_loader(self) -> instaloader.Instaloader:
        """Instaloader bound to the saved session; reloaded when cookies.txt changes."""
        cookies = instagram_session.cookies_file()
        mtime = cookies.stat().st_mtime
        if self._loader is None or self._loader_mtime != mtime:
            loader = instaloader.Instaloader(
                user_agent=instagram_session.user_agent(),
                iphone_support=False,
                quiet=True,
                max_connection_attempts=1,
            )
            session = instagram_session.read_cookies(cookies)
            if "sessionid" not in session or "csrftoken" not in session:
                raise DownloadError("cookies.txt has no sessionid/csrftoken: not logged in")
            loader.load_session(config.INSTAGRAM_USERNAME or "instagram", session)
            self._loader, self._loader_mtime = loader, mtime
        return self._loader

    def _instaloader_media(self, shortcode: str) -> list[tuple[str, bool]]:
        post = instaloader.Post.from_shortcode(self._get_loader().context, shortcode)
        if post.typename == "GraphSidecar":
            return [
                (node.video_url if node.is_video else node.display_url, node.is_video)
                for node in post.get_sidecar_nodes()
            ]
        if post.is_video:
            return [(post.video_url, True)]
        return [(post.url, False)]

    async def _via_instaloader(self, shortcode: str, dest: Path) -> list[Path]:
        media = await asyncio.to_thread(self._instaloader_media, shortcode)
        headers = {"User-Agent": instagram_session.user_agent()}
        return [
            await download_file(media_url, dest / f"{i:02d}.{'mp4' if video else 'jpg'}", headers)
            for i, (media_url, video) in enumerate(media)
            if media_url
        ]

    async def _via_reelsaver(self, url: str, dest: Path) -> list[Path]:
        """Third-party anonymous API; works for some public reels."""
        headers = {"User-Agent": instagram_session.user_agent()}
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            api_url = f"{REELSAVER_API}?postUrl={quote(url, safe='')}"
            async with session.get(api_url, headers=headers) as resp:
                data = await resp.json(content_type=None)
        video_url = (data.get("data") or {}).get("videoUrl")
        if data.get("status") != "success" or not video_url:
            raise DownloadError(f"ReelSaver: {data.get('message', data.get('status'))}")
        headers["Referer"] = "https://www.instagram.com/"
        return [await download_file(video_url, dest / "reel.mp4", headers)]
