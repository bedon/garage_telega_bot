import io
import os
import re
import tempfile
from urllib.parse import quote
import subprocess
import logging
from pathlib import Path
import aiohttp
import asyncio
import random
from telegram import Update
from utils import delete_message
from . import BaseHandler

INSTAGRAM_COOKIES_FILE = os.getenv("INSTAGRAM_COOKIES_FILE")

try:
    import instaloader

    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False

logger = logging.getLogger(__name__)

USE_DD_LINK = False  # DD Instagram service is down
# USE_YD = False

# Regex to extract Instagram URL from message (reel/reels/p)
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels)/[^\s]+", re.IGNORECASE
)

REELSAVER_API = "https://reelsaver.vercel.app/api/video"


class InstagramHandler(BaseHandler):
    def __init__(self):
        logger.info("Initializing InstagramHandler")
        self.INSTAGRAM_LINKS = [
            "instagram.com/reel/",
            "instagram.com/reels/",
            "instagram.com/p/",
        ]

        # Check if yt-dlp is available
        try:
            logger.debug("Checking if yt-dlp is available")
            subprocess.run(
                ["yt-dlp", "--version"], capture_output=True, text=True, check=True
            )
            self.yt_dlp_available = True
            logger.info("yt-dlp is available")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.yt_dlp_available = False
            logger.warning(f"yt-dlp is not available: {str(e)}")

        # Check if ffmpeg is available (still needed as fallback)
        try:
            logger.debug("Checking if ffmpeg is available")
            subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, check=True
            )
            self.ffmpeg_available = True
            logger.info("ffmpeg is available")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.ffmpeg_available = False
            logger.warning(f"ffmpeg is not available: {str(e)}")

        self.USER_AGENTS = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 12; Mobile; rv:104.0) Gecko/104.0 Firefox/104.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
        ]

        # Max file size for Telegram (8MB to be safe)
        self.MAX_FILE_SIZE_KB = 50000
        logger.debug(f"Max file size set to {self.MAX_FILE_SIZE_KB}KB")

        # Session for reusing connections and cookies
        self.session = None

        # Instaloader instance (reuse to maintain session)
        self._instaloader_instance = None
        self._last_request_time = 0

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.INSTAGRAM_LINKS)

    def _extract_url(self, message: str) -> str | None:
        """Extract Instagram URL from message (handles extra text around the link)."""
        match = INSTAGRAM_URL_PATTERN.search(message)
        return match.group(0).rstrip(".,;:!?)") if match else None

    def get_random_user_agent(self):
        return random.choice(self.USER_AGENTS)

    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout, cookie_jar=aiohttp.CookieJar()
            )
        return self.session

    async def download_with_retry(self, url, max_retries=3):
        """Download with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(random.uniform(1, 3))  # Random delay
                session = await self.get_session()
                headers = {"User-Agent": self.get_random_user_agent()}

                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        logger.warning(
                            f"Request failed with status {resp.status} on attempt {attempt + 1}"
                        )

            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise e
        return None

    async def is_dd_link_working(self, dd_link: str) -> bool:
        if not USE_DD_LINK:
            return False

        logger.debug(f"Checking if DD link is working: {dd_link}")
        try:
            await asyncio.sleep(random.uniform(0.5, 1.5))  # Random delay
            session = await self.get_session()
            headers = {"User-Agent": self.get_random_user_agent()}

            logger.debug(f"Sending GET request to {dd_link}")
            async with session.get(dd_link, timeout=10, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"DD link returned non-200 status: {resp.status}")
                    return False
                logger.debug("DD link is working (status 200)")
                return True
        except Exception as e:
            logger.error(f"Error checking DD link: {str(e)}")
            return False

    async def _download_via_reelsaver(self, url: str) -> bytes | None:
        """Get video URL from ReelSaver API, download with browser User-Agent, return bytes."""
        try:
            api_url = f"{REELSAVER_API}?postUrl={quote(url, safe='')}"
            headers = {"User-Agent": self.get_random_user_agent()}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url, headers=headers, timeout=30
                ) as response:
                    data = await response.json()
            if data.get("status") != "success" or not data.get("data", {}).get(
                "videoUrl"
            ):
                logger.warning(
                    "Instagram ReelSaver API failed: status=%s msg=%s",
                    data.get("status"),
                    data.get("message", data),
                )
                return None
            video_url = data["data"]["videoUrl"]
            headers["Referer"] = "https://www.instagram.com/"
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, headers=headers, timeout=60) as resp:
                    if resp.status != 200:
                        logger.warning("Instagram CDN returned status %s", resp.status)
                        return None
                    return await resp.read()
        except Exception as e:
            logger.warning("Instagram ReelSaver download failed: %s", e, exc_info=True)
            return None

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        url = self._extract_url(message)
        if not url:
            logger.warning("Instagram: no URL found in message: %s", message[:80])
            return

        logger.info("Instagram: processing %s", url)
        instagram_link = f'<a href="{url}">📸 Instagram</a>'

        try:
            # 1. Try ReelSaver API first (free, no login, similar to tikwm for TikTok)
            video_bytes = await self._download_via_reelsaver(url)
            if video_bytes:
                logger.info(
                    "Instagram: ReelSaver success, sending video (%d bytes)",
                    len(video_bytes),
                )
                video_io = io.BytesIO(video_bytes)
                video_io.seek(0)
                await update.message.chat.send_video(
                    video=video_io,
                    caption=self._format_caption(sender_name, instagram_link),
                    parse_mode="HTML",
                    supports_streaming=True,
                )
                await delete_message(update)
                return

            logger.info("Instagram: ReelSaver failed, trying yt-dlp fallback")

            # 2. Try ddinstagram link (if enabled)
            if USE_DD_LINK:
                dd_message = url.replace("instagram", "ddinstagram")
                if await self.is_dd_link_working(dd_message):
                    message_text = f"{dd_message}\n\n{sender_name}from 📸 Instagram"
                    await update.message.chat.send_message(
                        text=message_text,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                    )
                    await delete_message(update)
                    return

            # 3. Try yt-dlp fallback (may require cookies for some posts)
            instagram_id_match = re.search(r"/(?:p|reels?)/([^/?]+)", url)
            instagram_id = instagram_id_match.group(1) if instagram_id_match else "post"

            if not self.yt_dlp_available or not self.ffmpeg_available:
                logger.warning("Instagram: yt-dlp/ffmpeg not available for fallback")
                return

            # Try to download the video with yt-dlp
            try:
                logger.debug("Creating temporary directory for downloads")
                with tempfile.TemporaryDirectory() as temp_dir:
                    logger.debug(f"Temp directory created: {temp_dir}")
                    # Define format preferences in order - these are yt-dlp format selectors
                    format_preferences = [
                        # Try 720p video with audio (approx HD)
                        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
                        # Fallback to best format
                        "best",
                    ]

                    # Try each format preference in order
                    for i, format_selector in enumerate(format_preferences):
                        output_path = (
                            Path(temp_dir) / f"instagram_{instagram_id}_{i}.mp4"
                        )
                        logger.info(
                            f"Attempting format {i + 1}/{len(format_preferences)}: {format_selector}"
                        )

                        # Add random delay before download attempt
                        await asyncio.sleep(random.uniform(1, 3))

                        download_cmd = [
                            "yt-dlp",
                            "--no-warnings",
                            "--no-check-certificate",
                            "--user-agent",
                            self.get_random_user_agent(),
                        ]
                        if INSTAGRAM_COOKIES_FILE and os.path.isfile(
                            INSTAGRAM_COOKIES_FILE
                        ):
                            download_cmd.extend(["--cookies", INSTAGRAM_COOKIES_FILE])
                            logger.info(
                                "Instagram: using cookies from %s",
                                INSTAGRAM_COOKIES_FILE,
                            )
                        elif INSTAGRAM_COOKIES_FILE:
                            logger.warning(
                                "Instagram: INSTAGRAM_COOKIES_FILE set but file not found: %s",
                                INSTAGRAM_COOKIES_FILE,
                            )
                        download_cmd.extend(
                            [
                                "--sleep-interval",
                                "3",
                                "--max-sleep-interval",
                                "8",
                                "--sleep-requests",
                                "2",
                                "--retries",
                                "3",
                                "--fragment-retries",
                                "3",
                                "-f",
                                format_selector,
                                "--merge-output-format",
                                "mp4",
                                "-o",
                                str(output_path),
                                url,
                            ]
                        )

                        logger.debug(
                            f"Running download command: {' '.join(download_cmd)}"
                        )
                        # Run the download command
                        download_process = subprocess.run(
                            download_cmd, capture_output=True, text=True
                        )

                        # Check if download succeeded
                        if download_process.returncode == 0 and output_path.exists():
                            logger.info(f"Download succeeded with format {i + 1}")
                            # Check file size
                            file_size_kb = os.path.getsize(output_path) / 1024
                            logger.debug(f"File size: {file_size_kb:.2f}KB")

                            # If file is small enough, send it to Telegram
                            if file_size_kb <= self.MAX_FILE_SIZE_KB:
                                logger.info(
                                    f"File size {file_size_kb:.2f}KB is within limit, sending to Telegram"
                                )
                                await update.message.chat.send_video(
                                    video=open(output_path, "rb"),
                                    caption=self._format_caption(
                                        sender_name, instagram_link
                                    ),
                                    parse_mode="HTML",
                                    supports_streaming=True,
                                )
                                await delete_message(update)
                                logger.debug("Video sent and original message deleted")
                                return
                            # If this is the last format option and still too large, try to compress it
                            elif i == len(format_preferences) - 1:
                                logger.info(
                                    f"File too large ({file_size_kb:.2f}KB), trying compression"
                                )
                                compressed_path = await self.compress_video(
                                    output_path, temp_dir, instagram_id
                                )

                                if compressed_path and os.path.exists(compressed_path):
                                    compressed_size_kb = (
                                        os.path.getsize(compressed_path) / 1024
                                    )
                                    logger.info(
                                        f"Compression resulted in file size: {compressed_size_kb:.2f}KB"
                                    )

                                    if compressed_size_kb <= self.MAX_FILE_SIZE_KB:
                                        logger.info(
                                            "Compressed file is within size limit, sending to Telegram"
                                        )
                                        await update.message.chat.send_video(
                                            video=open(compressed_path, "rb"),
                                            caption=self._format_caption(
                                                sender_name, instagram_link
                                            ),
                                            parse_mode="HTML",
                                            supports_streaming=True,
                                        )
                                        await delete_message(update)
                                        logger.debug(
                                            "Compressed video sent and original deleted"
                                        )
                                        return
                                    else:
                                        logger.warning(
                                            f"Compressed file still too large: {compressed_size_kb:.2f}KB"
                                        )
                                else:
                                    logger.error("Compression failed")
                    else:
                        stderr = (download_process.stderr or "").strip()
                        # Log last 300 chars (yt-dlp puts the actual error at the end)
                        stderr_preview = stderr[-300:] if len(stderr) > 300 else stderr
                        logger.warning(
                            "Instagram yt-dlp format %s failed (returncode=%s): %s",
                            i + 1,
                            download_process.returncode,
                            stderr_preview or "no output",
                        )

            except Exception as e:
                logger.error("Instagram yt-dlp exception: %s", e, exc_info=True)

            logger.warning("Instagram: all download methods failed for %s", url)
        except Exception as e:
            logger.error("Instagram handler exception: %s", e, exc_info=True)
            # Don't send any error message to Telegram, just log it

    async def compress_video(self, input_path, temp_dir, instagram_id):
        """Fallback compression using FFmpeg if direct download is too large"""
        logger.info(f"Compressing video: {input_path}")
        try:
            compressed_path = (
                Path(temp_dir) / f"instagram_compressed_{instagram_id}.mp4"
            )
            logger.debug(f"Compressed path will be: {compressed_path}")

            # Compression settings for smaller file size
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                str(input_path),
                "-vf",
                "scale=480:-2",  # 480p resolution
                "-c:v",
                "libx264",
                "-preset",
                "faster",
                "-crf",
                "28",  # Lower but still acceptable quality
                "-maxrate",
                "800k",
                "-bufsize",
                "1200k",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-y",
                str(compressed_path),
            ]

            logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            compression_process = subprocess.run(
                ffmpeg_cmd, capture_output=True, text=True
            )

            if compression_process.returncode != 0:
                logger.error(f"FFmpeg compression failed: {compression_process.stderr}")
                return None

            return compressed_path
        except Exception as e:
            logger.error(f"Exception in compress_video: {str(e)}", exc_info=True)
            return None

    def get_instaloader_instance(self, temp_dir):
        """Get or create instaloader instance with session reuse."""
        if self._instaloader_instance is None:
            self._instaloader_instance = instaloader.Instaloader(
                dirname_pattern=temp_dir,
                filename_pattern="instagram_{shortcode}",
                download_pictures=False,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                sleep=True,
                max_connection_attempts=3,
            )
        return self._instaloader_instance

    async def try_instaloader_download(
        self, update, message, sender_name, instagram_link, instagram_id
    ):
        """Try downloading with instaloader with aggressive rate limiting"""
        logger.info("Attempting download with instaloader")

        try:
            # Rate limiting - wait at least 10 seconds between requests
            import time

            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < 10:
                wait_time = 10 - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()

            with tempfile.TemporaryDirectory() as temp_dir:
                # Get reusable instaloader instance
                L = self.get_instaloader_instance(temp_dir)

                # Extract shortcode from URL
                shortcode_match = re.search(r"/(?:p|reels?)/([^/?]+)", message)
                if not shortcode_match:
                    return False

                shortcode = shortcode_match.group(1)
                logger.info(f"Downloading shortcode: {shortcode}")

                # Add additional delay before request
                await asyncio.sleep(random.uniform(2, 5))

                # Download the post
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=temp_dir)

                # Find the downloaded video file
                video_files = list(Path(temp_dir).glob("*.mp4"))
                if not video_files:
                    logger.warning("No video files found after instaloader download")
                    return False

                video_path = video_files[0]
                file_size_kb = os.path.getsize(video_path) / 1024
                logger.info(f"Instaloader downloaded video: {file_size_kb:.2f}KB")

                # Check file size and send
                if file_size_kb <= self.MAX_FILE_SIZE_KB:
                    await update.message.chat.send_video(
                        video=open(video_path, "rb"),
                        caption=self._format_caption(sender_name, instagram_link),
                        parse_mode="HTML",
                        supports_streaming=True,
                    )
                    await delete_message(update)
                    logger.info("Video sent successfully via instaloader")
                    return True
                else:
                    logger.warning(f"Instaloader video too large: {file_size_kb:.2f}KB")
                    return False

        except Exception as e:
            logger.error(f"Instaloader download failed: {str(e)}")
            # Reset instance on failure to get fresh session
            self._instaloader_instance = None
            return False

    async def cleanup(self):
        """Cleanup session resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
