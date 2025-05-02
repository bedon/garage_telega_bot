import re
import os
import tempfile
import subprocess
import logging
from pathlib import Path
import aiohttp
from telegram import Update
from utils import delete_message
from . import BaseHandler

logger = logging.getLogger(__name__)

class InstagramHandler(BaseHandler):
    def __init__(self):
        logger.info("Initializing InstagramHandler")
        self.INSTAGRAM_LINKS = ["instagram.com/reel/", "instagram.com/p/"]

        # Check if yt-dlp is available
        try:
            logger.debug("Checking if yt-dlp is available")
            subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
            self.yt_dlp_available = True
            logger.info("yt-dlp is available")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.yt_dlp_available = False
            logger.warning(f"yt-dlp is not available: {str(e)}")

        # Check if ffmpeg is available (still needed as fallback)
        try:
            logger.debug("Checking if ffmpeg is available")
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
            self.ffmpeg_available = True
            logger.info("ffmpeg is available")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.ffmpeg_available = False
            logger.warning(f"ffmpeg is not available: {str(e)}")

        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Max file size for Telegram (8MB to be safe)
        self.MAX_FILE_SIZE_KB = 8000
        logger.debug(f"Max file size set to {self.MAX_FILE_SIZE_KB}KB")

    def can_handle(self, message: str) -> bool:
        result = any(link in message.lower() for link in self.INSTAGRAM_LINKS)
        logger.debug(f"Can handle check for '{message[:50]}...': {result}")
        return result

    async def is_dd_link_working(self, dd_link: str) -> bool:
        logger.debug(f"Checking if DD link is working: {dd_link}")
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Sending GET request to {dd_link}")
                async with session.get(dd_link, timeout=10, headers={"User-Agent": self.USER_AGENT}) as resp:
                    if resp.status != 200:
                        logger.warning(f"DD link returned non-200 status: {resp.status}")
                        return False
                    logger.debug(f"DD link is working (status 200)")
                    return True
        except Exception as e:
            logger.error(f"Error checking DD link: {str(e)}")
            return False

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        logger.info(f"Handling Instagram link: {message}")
        instagram_link = f'<a href="{message}">📸 Instagram</a>'

        try:
            # Extract post ID
            logger.debug("Extracting Instagram post ID")
            instagram_id_match = re.search(r'/(?:p|reel)/([^/?]+)', message)
            if not instagram_id_match:
                logger.warning(f"Invalid Instagram link format: {message}")
                await update.message.chat.send_message(
                    f"{sender_name} 📸 Instagram\n\n[Invalid Instagram link] {message}"
                )
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
                    text=message_text,
                    parse_mode="HTML",  # Use HTML for other formatting if needed
                    disable_web_page_preview=False  # Ensure preview is enabled
                )
    
                await delete_message(update)
                logger.debug("Message sent and original deleted")
                return

            logger.debug("DD link not working, falling back to original link")
            instagram_link = f'<a href="{message}">📸 Instagram</a>'

            # Check for required tools
            if not self.yt_dlp_available:
                logger.error("yt-dlp not available, aborting")
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error: yt-dlp is not installed. Please install it with: pip install yt-dlp",
                    parse_mode="HTML"
                )
                return

            if not self.ffmpeg_available:
                logger.error("ffmpeg not available, aborting")
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error: ffmpeg is not installed. Please install ffmpeg for video compression.",
                    parse_mode="HTML"
                )
                return

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
                        "best"
                    ]

                    # Try each format preference in order
                    for i, format_selector in enumerate(format_preferences):
                        output_path = Path(temp_dir) / f"instagram_{instagram_id}_{i}.mp4"
                        logger.info(f"Attempting format {i+1}/{len(format_preferences)}: {format_selector}")

                        download_cmd = [
                            "yt-dlp",
                            "--no-warnings",
                            "--no-check-certificate",
                            "--user-agent", self.USER_AGENT,
                            "-f", format_selector,
                            "--merge-output-format", "mp4",
                            "-o", str(output_path),
                            message
                        ]

                        logger.debug(f"Running download command: {' '.join(download_cmd)}")
                        # Run the download command
                        download_process = subprocess.run(download_cmd, capture_output=True, text=True)

                        # Check if download succeeded
                        if download_process.returncode == 0 and output_path.exists():
                            logger.info(f"Download succeeded with format {i+1}")
                            # Check file size
                            file_size_kb = os.path.getsize(output_path) / 1024
                            logger.debug(f"File size: {file_size_kb:.2f}KB")

                            # If file is small enough, send it to Telegram
                            if file_size_kb <= self.MAX_FILE_SIZE_KB:
                                logger.info(f"File size {file_size_kb:.2f}KB is within limit, sending to Telegram")
                                await update.message.chat.send_video(
                                    video=open(output_path, 'rb'),
                                    caption=self._format_caption(sender_name, instagram_link),
                                    parse_mode="HTML",
                                    supports_streaming=True
                                )
                                await delete_message(update)
                                logger.debug("Video sent and original message deleted")
                                return
                            # If this is the last format option and still too large, try to compress it
                            elif i == len(format_preferences) - 1:
                                logger.info(f"File too large ({file_size_kb:.2f}KB), trying compression")
                                compressed_path = await self.compress_video(output_path, temp_dir, instagram_id)

                                if compressed_path and os.path.exists(compressed_path):
                                    compressed_size_kb = os.path.getsize(compressed_path) / 1024
                                    logger.info(f"Compression resulted in file size: {compressed_size_kb:.2f}KB")

                                    if compressed_size_kb <= self.MAX_FILE_SIZE_KB:
                                        logger.info("Compressed file is within size limit, sending to Telegram")
                                        await update.message.chat.send_video(
                                            video=open(compressed_path, 'rb'),
                                            caption=self._format_caption(sender_name, instagram_link),
                                            parse_mode="HTML",
                                            supports_streaming=True
                                        )
                                        await delete_message(update)
                                        logger.debug("Compressed video sent and original deleted")
                                        return
                                    else:
                                        logger.warning(f"Compressed file still too large: {compressed_size_kb:.2f}KB")
                                else:
                                    logger.error("Compression failed")
                        else:
                            logger.warning(f"Download failed with format {i+1}")
                            if download_process.stderr:
                                logger.error(f"Error output: {download_process.stderr}")

                    # If we got here, all format attempts failed or were too large
                    logger.warning("All format attempts failed or resulted in files too large")
                    # Try to get just a thumbnail
                    logger.info("Attempting to send thumbnail as fallback")
                    success = await self.send_thumbnail_fallback(update, message, sender_name, instagram_id, instagram_link, temp_dir)
                    if not success:
                        # If thumbnail fails, send just the link
                        logger.warning("Thumbnail fallback failed, sending link only")
                        await update.message.chat.send_message(
                            self._format_caption(sender_name, instagram_link) + "\n\n"
                            f"Unable to process video. Watch by original link:\n\n"
                            f"{message}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)

            except Exception as e:
                logger.error(f"Exception in main processing: {str(e)}", exc_info=True)
                # If all else fails, send just the link
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error processing content. Try opening the original link.",
                    parse_mode="HTML"
                )
                await delete_message(update)
        except Exception as e:
            logger.error(f"Outer exception in handle method: {str(e)}", exc_info=True)
            await update.message.chat.send_message(
                self._format_caption(sender_name, instagram_link) + "\n\n"
                f"Error processing content. Try opening the original link.",
                parse_mode="HTML"
            )
            await delete_message(update)

    async def compress_video(self, input_path, temp_dir, instagram_id):
        """Fallback compression using FFmpeg if direct download is too large"""
        logger.info(f"Compressing video: {input_path}")
        try:
            compressed_path = Path(temp_dir) / f"instagram_compressed_{instagram_id}.mp4"
            logger.debug(f"Compressed path will be: {compressed_path}")

            # Compression settings for smaller file size
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-vf", "scale=480:-2",                # 480p resolution
                "-c:v", "libx264",
                "-preset", "faster",
                "-crf", "28",                         # Lower but still acceptable quality
                "-maxrate", "800k",
                "-bufsize", "1200k",
                "-movflags", "+faststart",
                "-c:a", "aac",
                "-b:a", "64k",
                "-y",
                str(compressed_path)
            ]

            logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            compression_process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if compression_process.returncode == 0:
                logger.info("Compression successful")
                compressed_size = os.path.getsize(compressed_path) / 1024
                logger.debug(f"Compressed file size: {compressed_size:.2f}KB")
                return compressed_path
            else:
                logger.error(f"Compression failed with return code {compression_process.returncode}")
                if compression_process.stderr:
                    logger.error(f"Compression error: {compression_process.stderr}")
                return None
        except Exception as e:
            logger.error(f"Exception during compression: {str(e)}", exc_info=True)
            return None

    async def send_thumbnail_fallback(self, update, message, sender_name, instagram_id, instagram_link, temp_dir):
        """Send thumbnail as fallback when video can't be sent"""
        logger.info(f"Attempting to send thumbnail fallback for {instagram_id}")
        try:
            thumb_path = Path(temp_dir) / f"instagram_thumb_{instagram_id}"
            logger.debug(f"Thumbnail path base: {thumb_path}")

            thumb_cmd = [
                "yt-dlp",
                "--no-warnings",
                "--skip-download",
                "--write-thumbnail",
                "-o", str(thumb_path),
                message
            ]

            logger.debug(f"Thumbnail command: {' '.join(thumb_cmd)}")
            process_result = subprocess.run(thumb_cmd, capture_output=True, text=True)

            if process_result.returncode != 0:
                logger.error(f"Thumbnail download failed: {process_result.stderr}")
                return False

            # Find thumbnail file (might have different extension)
            logger.debug(f"Looking for thumbnail files matching: {thumb_path}.*")
            thumb_files = list(Path(temp_dir).glob(f"instagram_thumb_{instagram_id}.*"))
            logger.debug(f"Found {len(thumb_files)} thumbnail files")

            if thumb_files:
                thumb_file = thumb_files[0]
                logger.info(f"Using thumbnail file: {thumb_file}")
                file_size_kb = os.path.getsize(thumb_file) / 1024
                logger.debug(f"Thumbnail size: {file_size_kb:.2f}KB")

                await update.message.chat.send_photo(
                    photo=open(thumb_file, 'rb'),
                    caption=self._format_caption(sender_name, instagram_link) + "\n(Unable to send video, see original link)",
                    parse_mode="HTML"
                )
                await delete_message(update)
                logger.info("Thumbnail sent successfully")
                return True
            else:
                logger.warning("No thumbnail files found")
                return False
        except Exception as e:
            logger.error(f"Exception in thumbnail fallback: {str(e)}", exc_info=True)
            return False
