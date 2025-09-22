import re
import os
import tempfile
import subprocess
import logging
from pathlib import Path
import aiohttp
import asyncio
import random
from telegram import Update
from utils import delete_message
from . import BaseHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

USE_DD_LINK = True


class InstagramHandler(BaseHandler):
    def __init__(self):
        logger.info("Initializing InstagramHandler")
        self.INSTAGRAM_LINKS = ["instagram.com/reel/", "instagram.com/p/"]

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
        self.MAX_FILE_SIZE_KB = 8000
        logger.debug(f"Max file size set to {self.MAX_FILE_SIZE_KB}KB")

        # Session for reusing connections and cookies
        self.session = None

    def can_handle(self, message: str) -> bool:
        result = any(link in message.lower() for link in self.INSTAGRAM_LINKS)
        logger.debug(f"Can handle check for '{message[:50]}...': {result}")
        return result

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
                logger.debug(f"DD link is working (status 200)")
                return True
        except Exception as e:
            logger.error(f"Error checking DD link: {str(e)}")
            return False

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            # Extract post ID
            logger.debug("Extracting Instagram post ID")
            instagram_id_match = re.search(r"/(?:p|reel)/([^/?]+)", message)
            if not instagram_id_match:
                logger.warning(f"Invalid Instagram link format: {message}")
                return

            instagram_id = instagram_id_match.group(1)
            logger.info(f"Instagram ID extracted: {instagram_id}")

            # Try ddinstagram link first
            dd_message = message.replace("instagram", "ddinstagram")
            logger.debug(f"Trying ddinstagram link: {dd_message}")

            if await self.is_dd_link_working(dd_message):
                logger.info("DD link is working, sending message with DD link")

                # Format with emoji but keep the URL separate for preview
                message_text = f"{dd_message}\n\n{sender_name}from 📸 Instagram"

                await update.message.chat.send_message(
                    text=message_text, parse_mode="HTML", disable_web_page_preview=False
                )

                await delete_message(update)
                logger.debug("Message sent and original deleted")
                return

            logger.debug("DD link not working, falling back to original link")
            instagram_link = f'<a href="{message}">📸 Instagram</a>'

            # Check for required tools
            if not self.yt_dlp_available or not self.ffmpeg_available:
                logger.warning("Required tools not available")
                return

            # Try to download the video
            try:
                logger.debug("Creating temporary directory for downloads")
                with tempfile.TemporaryDirectory() as temp_dir:
                    logger.debug(f"Temp directory created: {temp_dir}")
                    # Define format preferences in order - these are yt-dlp format selectors
                    format_preferences = [
                        # Try 720p video with audio (approx HD)
                        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
                        # Try 480p video with audio (approx SD)
                        "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
                        # Try 360p video with audio (low quality)
                        "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]",
                        # Fallback to any format that's less than 8MB
                        "best[filesize<8M]",
                        # Last resort, best format
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
                            "-f",
                            format_selector,
                            "--merge-output-format",
                            "mp4",
                            "--sleep-interval",
                            "1",
                            "--max-sleep-interval",
                            "3",
                            "-o",
                            str(output_path),
                            message,
                        ]

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
                        logger.warning(f"Download failed with format {i + 1}")
                        if download_process.stderr:
                            logger.error(f"Error output: {download_process.stderr}")

            except Exception as e:
                logger.error(f"Exception in main processing: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Outer exception in handle method: {str(e)}", exc_info=True)
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

    async def cleanup(self):
        """Cleanup session resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

