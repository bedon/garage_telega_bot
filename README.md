# Social Media Video Downloader Bot

A Telegram bot that downloads videos (and Instagram photos/carousels) from Instagram, Facebook, X/Twitter and TikTok links posted in a chat, re-posts the media and deletes the original message.

## Features

- Instagram reels, posts, carousels (sent as albums), `/tv/` and `/share/` links
- TikTok (via tikwm, falls back to yt-dlp), X/Twitter and Facebook (via yt-dlp)
- Links work anywhere in a message, with extra text around them
- Downloads run in the background, so one slow video never blocks the bot
- Videos over Telegram's 50 MB limit are re-encoded with ffmpeg to fit
- Automatic handler discovery

## Setup

Requirements: Python 3.11+, `ffmpeg` (`apt install ffmpeg` / `brew install ffmpeg`).

```bash
git clone <repository-url>
cd garage_telega_bot
make setup              # creates venv, installs requirements
cp .env.example .env    # then set TELEGRAM_TOKEN
make dev                # run in the foreground (make dev-verbose for INFO logs)
```

On the server, `make run` / `make stop` / `make deploy` (pull, upgrade deps, restart). Logs go to `bot.log`.

### Docker

```bash
docker build -t garage-bot .
docker run -d --env-file .env -v $PWD/data:/app/data garage-bot
# Instagram login inside the container:
docker run -it --rm --env-file .env -v $PWD/data:/app/data garage-bot python src/ig_login.py
```

## Environment variables

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) (required) |
| `LOG_LEVEL` | `ERROR` (default), `INFO`, `DEBUG` |
| `INSTAGRAM_USERNAME` / `INSTAGRAM_PASSWORD` | Used only by `make ig-login` |
| `INSTAGRAM_DATA_DIR` | Where the Instagram session is stored (default `data/instagram`) |
| `INSTAGRAM_COOKIES_FILE` | Use your own Netscape cookies file instead of `data/instagram/cookies.txt` |
| `MAX_UPLOAD_MB` | Upload limit (default 50) |
| `MAX_PARALLEL_DOWNLOADS` | Concurrent downloads (default 2) |

## Instagram

Many public reels download without logging in. From a server (datacenter IP) Instagram usually demands a login, so give the bot a session.

**Why exporting cookies from your laptop doesn't work well:** Instagram ties a session to the device and location it was created on. Cookies from your laptop's browser used from a server in another country, with a different User-Agent, look like a stolen session and get revoked. The session has to be created **from the server's IP** and always used with **one fixed User-Agent**. The bot handles the User-Agent part; you only need to log in from the server.

### Option 1: `make ig-login` (recommended)

Over SSH, on the server:

```bash
make ig-login     # uses INSTAGRAM_USERNAME/PASSWORD from .env, or asks; asks for a 2FA code if enabled
make ig-check     # verifies the saved session still works
```

This saves `data/instagram/cookies.txt` and `data/instagram/user_agent.txt`. The running bot picks up a new session automatically, so no restart is needed.

If Instagram asks for a **checkpoint**, the script prints a full `https://www.instagram.com/auth_platform/...` link and waits. **Leave it running.** Open the link in a browser logged into the same account (or tap "This was me" in the Instagram app), then press Enter so the script retries. Don't restart the script: each new run triggers a new checkpoint. If the link shows no prompt, use Option 2.

### Option 2: log in through the browser via an SSH tunnel

If the login script is blocked, log in with a real browser while routing its traffic through the server, so Instagram still sees the server's IP:

```bash
ssh -D 1080 -N user@your-server          # leave running
# macOS; on Linux run google-chrome with the same flags
open -na "Google Chrome" --args --proxy-server="socks5://127.0.0.1:1080" --user-data-dir=/tmp/ig-profile
```

1. In that browser window, check https://ifconfig.me shows the server IP, then log in to instagram.com.
2. Export cookies for instagram.com with [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Netscape format).
3. Copy the browser's User-Agent (open `chrome://version`).
4. Upload both:

```bash
scp cookies.txt user@your-server:/path/to/garage_telega_bot/data/instagram/cookies.txt
ssh user@your-server 'echo "<paste user agent>" > /path/to/garage_telega_bot/data/instagram/user_agent.txt'
```

### When it stops working

- The log shows `Instagram session looks expired or flagged`: run `make ig-login` again.
- Downloads fail across the board: run `make update-ytdlp` (Instagram changes often; `make deploy` also upgrades).
- Use a dedicated Instagram account, not your personal one.

## How downloads work

| Platform | Order |
|---|---|
| Instagram reel | yt-dlp (with session if present) → instaloader (session only) → ReelSaver API |
| Instagram post `/p/` | instaloader first when a session exists (handles photos and carousels), then the same as a reel |
| TikTok | tikwm API → yt-dlp |
| X / Facebook | yt-dlp |

Shared code lives in `src/downloader.py`: `run_ytdlp`, `download_file`, `send_media` (video/photo/album + deletes the original), `fit_to_limit` (ffmpeg compression) and `download_and_send`.

## Adding a handler

Create `src/handlers/<name>_handler.py` with a `BaseHandler` subclass. It is discovered automatically.

```python
import re
from downloader import download_and_send
from . import BaseHandler


class YouTubeHandler(BaseHandler):
    URL_PATTERN = re.compile(r"https?://(?:www\.)?(?:youtube\.com/shorts/|youtu\.be/)[^\s]+")

    async def handle(self, update, message: str, sender_name: str) -> None:
        url = self.extract_url(message)
        await download_and_send(update, url, self._format_caption(sender_name, url, "📺 YouTube"))
```

`BaseHandler` provides `can_handle()` / `extract_url()` from `URL_PATTERN` and `_format_caption()` (HTML-escaped link).

## Tests

```bash
make install   # includes requirements-dev.txt
make test
```
