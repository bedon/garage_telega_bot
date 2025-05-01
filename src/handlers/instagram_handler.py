import re
import os
import tempfile
import subprocess
from pathlib import Path
import io

from telegram import Update

from utils import delete_message
from . import BaseHandler


class InstagramHandler(BaseHandler):
    def __init__(self):
        self.INSTAGRAM_LINKS = ["instagram.com/reel/", "instagram.com/p/"]
        # Check if yt-dlp is available
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
            self.yt_dlp_available = True
        except (subprocess.SubprocessError, FileNotFoundError):
            self.yt_dlp_available = False
            
        # Check if ffmpeg is available (still needed as fallback)
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
            self.ffmpeg_available = True
        except (subprocess.SubprocessError, FileNotFoundError):
            self.ffmpeg_available = False
            
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Max file size for Telegram (8MB to be safe)
        self.MAX_FILE_SIZE_KB = 8000

    def can_handle(self, message: str) -> bool:
        return any(link in message.lower() for link in self.INSTAGRAM_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            # Extract post ID
            instagram_id_match = re.search(r'/(?:p|reel)/([^/?]+)', message)
            if not instagram_id_match:
                await update.message.chat.send_message(
                    f"{sender_name} 📸 Instagram\n\n[Invalid Instagram link] {message}"
                )
                return

            instagram_id = instagram_id_match.group(1)
            instagram_link = f'<a href="{message}">📸 Instagram</a>'
            
            # Check for required tools
            if not self.yt_dlp_available:
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error: yt-dlp is not installed. Please install it with: pip install yt-dlp",
                    parse_mode="HTML"
                )
                return
                
            if not self.ffmpeg_available:
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error: ffmpeg is not installed. Please install ffmpeg for video compression.",
                    parse_mode="HTML"
                )
                return
            
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
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
                        
                        # Run the download command
                        download_process = subprocess.run(download_cmd, capture_output=True, text=True)
                        
                        # Check if download succeeded
                        if download_process.returncode == 0 and output_path.exists():
                            # Check file size
                            file_size_kb = os.path.getsize(output_path) / 1024
                            
                            # If file is small enough, send it to Telegram
                            if file_size_kb <= self.MAX_FILE_SIZE_KB:
                                await update.message.chat.send_video(
                                    video=open(output_path, 'rb'),
                                    caption=self._format_caption(sender_name, instagram_link),
                                    parse_mode="HTML",
                                    supports_streaming=True
                                )
                                await delete_message(update)
                                return
                            # If this is the last format option and still too large, try to compress it
                            elif i == len(format_preferences) - 1:
                                compressed_path = await self.compress_video(output_path, temp_dir, instagram_id)
                                
                                if compressed_path and os.path.exists(compressed_path):
                                    compressed_size_kb = os.path.getsize(compressed_path) / 1024
                                    
                                    if compressed_size_kb <= self.MAX_FILE_SIZE_KB:
                                        await update.message.chat.send_video(
                                            video=open(compressed_path, 'rb'),
                                            caption=self._format_caption(sender_name, instagram_link),
                                            parse_mode="HTML",
                                            supports_streaming=True
                                        )
                                        await delete_message(update)
                                return
                    
                    # If we got here, all format attempts failed or were too large
                    # Try to get just a thumbnail
                    success = await self.send_thumbnail_fallback(update, message, sender_name, instagram_id, instagram_link, temp_dir)
                    if not success:
                        # If thumbnail fails, send just the link
                        await update.message.chat.send_message(
                            self._format_caption(sender_name, instagram_link) + "\n\n"
                            f"Unable to process video. Watch by original link:\n\n"
                            f"{message}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
            
            except Exception:
                # If all else fails, send just the link
                await update.message.chat.send_message(
                    self._format_caption(sender_name, instagram_link) + "\n\n"
                    f"Error processing content. Try opening the original link.",
                    parse_mode="HTML"
                )
                await delete_message(update)

        except Exception:
            await update.message.chat.send_message(
                self._format_caption(sender_name, instagram_link) + "\n\n"
                f"Error processing content. Try opening the original link.",
                parse_mode="HTML"
            )
            await delete_message(update)

    async def compress_video(self, input_path, temp_dir, instagram_id):
        """Fallback compression using FFmpeg if direct download is too large"""
        try:
            compressed_path = Path(temp_dir) / f"instagram_compressed_{instagram_id}.mp4"
            
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
            
            compression_process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if compression_process.returncode == 0 and compressed_path.exists():
                return compressed_path
            else:
                return None
        except Exception:
            return None

    async def send_thumbnail_fallback(self, update, message, sender_name, instagram_id, instagram_link, temp_dir):
        """Send thumbnail as fallback when video can't be sent"""
        try:
            thumb_path = Path(temp_dir) / f"instagram_thumb_{instagram_id}"
            thumb_cmd = [
                "yt-dlp",
                "--no-warnings",
                "--skip-download",
                "--write-thumbnail",
                "-o", str(thumb_path),
                message
            ]
            
            subprocess.run(thumb_cmd, capture_output=True, text=True)
            
            # Find thumbnail file (might have different extension)
            thumb_files = list(Path(temp_dir).glob(f"instagram_thumb_{instagram_id}.*"))
            if thumb_files:
                thumb_file = thumb_files[0]
                await update.message.chat.send_photo(
                    photo=open(thumb_file, 'rb'),
                    caption=self._format_caption(sender_name, instagram_link) + "\n(Unable to send video, see original link)",
                    parse_mode="HTML"
                )
                await delete_message(update)
                return True
            return False
        except Exception:
            return False