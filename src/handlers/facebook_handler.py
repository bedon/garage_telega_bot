import io
import subprocess
import tempfile
import os

from telegram import Update

from utils import delete_message


class FacebookHandler:
    def __init__(self):
        self.FACEBOOK_LINKS = ["https://www.facebook.com/reel/", "https://fb.watch/"]

    def can_handle(self, message: str) -> bool:
        return any(link in message for link in self.FACEBOOK_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            fb_link = f'<a href="{message}">📘 From Facebook</a>'

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
                        caption=f"{sender_name} {fb_link}",
                        parse_mode="HTML"
                    )
                    await delete_message(update)
                    return
            except Exception:
                pass

            # Try to download using temporary file
            try:
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "facebook_video.mp4")

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
                            caption=f"{sender_name} {fb_link}",
                            parse_mode="HTML"
                        )
                        await delete_message(update)
                        os.remove(output_path)
                        return
            except Exception:
                pass

            # If download failed
            await update.message.chat.send_message(
                f"{sender_name} {fb_link}\n\n"
                f"Failed to automatically download the video.\n"
                f"Watch by original link:\n\n"
                # f"1. https://fdown.net/\n"
                # f"2. https://snapvid.net/\n\n"
                f"Original link: {message}",
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error processing Facebook video: {e}")
            await update.message.chat.send_message(
                f"{sender_name} <a href='{message}'>📘 From Facebook</a>\n\n"
                f"Error processing video. Watch by original link:\n\n"
                # f"1. https://fdown.net/\n"
                # f"2. https://snapvid.net/\n\n"
                f"Original link: {message}",
                parse_mode="HTML"
            )
