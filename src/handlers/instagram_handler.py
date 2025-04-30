import re

import aiohttp
from telegram import Update

from utils import delete_message


class InstagramHandler:
    def __init__(self):
        self.INSTAGRAM_LINKS = ["https://www.instagram.com/reel/", "https://www.instagram.com/p/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.INSTAGRAM_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            # Extract post ID
            instagram_id_match = re.search(r'/(?:p|reel)/([^/?]+)', message)
            if not instagram_id_match:
                await update.message.chat.send_message(
                    f"{sender_name} 📸 From Instagram\n\n[Invalid Instagram link] {message}"
                )
                return

            instagram_id = instagram_id_match.group(1)
            instagram_link = f'<a href="{message}">📸 From Instagram</a>'

            # Try third-party API
            try:
                api_url = f"https://instagram-stories-api.vercel.app/api/post?url={message}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, timeout=20) as response:
                        if response.status == 200:
                            data = await response.json()

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

            # Final fallback: try parsing HTML source directly
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(message, headers=headers, timeout=15) as response:
                        html = await response.text()

                video_match = re.search(r'video_url":"([^"]+)"', html)
                if video_match:
                    video_url = video_match.group(1).replace("\\u0026", "&")
                    await update.message.chat.send_video(
                        video=video_url,
                        caption=f"{sender_name} {instagram_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return

                image_match = re.search(r'display_url":"([^"]+)"', html)
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

            # If all methods fail
            await update.message.chat.send_message(
                f"{sender_name} {instagram_link}\n\n"
                f"Failed to automatically download the video. Watch by original link :\n\n"
                # f"1. https://saveinsta.app/instagram-video-downloader/{instagram_id}\n"
                # f"2. https://www.y2mate.com/instagram/{instagram_id}\n"
                # f"3. https://sssinstagram.com/\n\n"
                f"Original link: {message}",
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error processing Instagram video: {e}")
            await update.message.chat.send_message(
                f"{sender_name} <a href='{message}'>📸 From Instagram</a>\n\n"
                f"Error processing video. Try downloading manually.",
                parse_mode="HTML"
            )
