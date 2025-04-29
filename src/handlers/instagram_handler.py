import io
import os
import re
import subprocess
import tempfile

import requests
from telegram import Update

from utils import delete_message


class InstagramHandler:
    def __init__(self):
        self.INSTAGRAM_LINKS = ["https://www.instagram.com/reel/", "https://www.instagram.com/p/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.INSTAGRAM_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            instagram_id_match = re.search(r'/(?:p|reel)/([^/?]+)', message)
            if not instagram_id_match:
                await update.message.chat.send_message(
                    f"{sender_name} 📸 From Instagram\n\n[Invalid Instagram link] {message}"
                )
                return

            instagram_id = instagram_id_match.group(1)
            instagram_link = f'<a href="{message}">📸 From Instagram</a>'

            # Try to download using yt-dlp directly to memory
            try:
                process = subprocess.run(
                    ["yt-dlp", "-o", "-", "--format", "best", message],
                    capture_output=True,
                    check=False
                )

                if process.stdout and len(process.stdout) > 0:
                    video_bytes = io.BytesIO(process.stdout)
                    video_bytes.seek(0)

                    await update.message.chat.send_video(
                        video=video_bytes,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                pass

            # Try to download using temporary file
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f"{instagram_id}.mp4")

                process = subprocess.run(
                    ["yt-dlp", "-o", output_path, "--format", "best", message],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    with open(output_path, "rb") as video_file:
                        await update.message.chat.send_video(
                            video=video_file,
                            caption=f"{sender_name} {instagram_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        os.remove(output_path)
                        return
            except Exception:
                pass

            # Try using third-party API
            try:
                api_url = f"https://instagram-stories-api.vercel.app/api/post?url={message}"
                response = requests.get(api_url, timeout=20)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("error") is None and data.get("download_url"):
                        if data.get("media_type") == "video":
                            await update.message.chat.send_video(
                                video=data["download_url"],
                                caption=f"{sender_name} {instagram_link}",
                                parse_mode="HTML"
                            )
                            await delete_message(update)
                            return
                        elif data.get("media_type") == "image":
                            await update.message.chat.send_photo(
                                photo=data["download_url"],
                                caption=f"{sender_name} {instagram_link}",
                                parse_mode="HTML"
                            )
                            await delete_message(update)
                            return
            except Exception:
                pass

            # Last attempt - parse the source page
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "max-age=0"
                }

                response = requests.get(message, headers=headers, timeout=15)

                video_match = re.search(r'video_url":"([^"]+)"', response.text)
                if video_match:
                    video_url = video_match.group(1).replace("\\u0026", "&")
                    await update.message.chat.send_video(
                        video=video_url,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return

                image_match = re.search(r'display_url":"([^"]+)"', response.text)
                if image_match:
                    image_url = image_match.group(1).replace("\\u0026", "&")
                    await update.message.chat.send_photo(
                        photo=image_url,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                pass

            # If all methods failed
            await update.message.chat.send_message(
                f"{sender_name} {instagram_link}\n\n"
                f"Failed to automatically download the video. Try these services:\n\n"
                f"1. https://saveinsta.app/instagram-video-downloader/{instagram_id}\n"
                f"2. https://www.y2mate.com/instagram/{instagram_id}\n"
                f"3. https://sssinstagram.com/\n\n"
                f"Original link: {message}",
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error processing Instagram video: {e}")
            await update.message.chat.send_message(
                f"{sender_name} <a href='{message}'>📸 From Instagram</a>\n\n"
                f"Error processing video. Try downloading manually through:\n\n"
                f"1. https://saveinsta.app/\n"
                f"2. https://instadownloader.co/\n\n"
                f"Original link: {message}",
                parse_mode="HTML"
            )
