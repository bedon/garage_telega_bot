# Garage Telega Bot

## Project Overview
Python Telegram bot that downloads videos/photos from social media links (Instagram, Facebook, X/Twitter, TikTok), re-posts them to the chat and deletes the original message.

## Architecture
- `src/main.py`: bot setup (`concurrent_updates`), message routing to the first matching handler
- `src/config.py`: all env/config (loads `.env` from the project root)
- `src/downloader.py`: shared async core: `run_ytdlp` (yt-dlp Python API in a thread), `download_file`, `fit_to_limit`/`compress_video` (ffmpeg), `send_media` (video/photo/album + delete original), `download_and_send`, `download_slot` semaphore
- `src/handlers/`: one `BaseHandler` subclass per platform, auto-discovered. Each sets `URL_PATTERN` and implements `handle()`
- `src/instagram_session.py`: Instagram session files (`data/instagram/cookies.txt` + `user_agent.txt`) shared by yt-dlp and instaloader
- `src/ig_login.py`: `make ig-login` / `make ig-check`; logs in with instaloader and writes the session
- `src/utils.py`: status prefix, handler loading, message deletion

## Rules
- Never call blocking code (`subprocess.run`, yt-dlp, instaloader) directly in async code: use `asyncio.to_thread` / `create_subprocess_exec`.
- Instagram requests must always use `instagram_session.user_agent()`. Rotating UAs gets the session revoked.
- Captions are HTML: escape user-provided text and URLs.

## Key Technologies
python-telegram-bot 22, yt-dlp, instaloader, aiohttp, ffmpeg (system dependency)

## Testing
`make test` (pytest, asyncio auto mode, `pythonpath = src`, so import modules as `handlers.x`, `downloader`, not `src.x`).

## Environment
`TELEGRAM_TOKEN` (required), `LOG_LEVEL`, `INSTAGRAM_USERNAME`/`INSTAGRAM_PASSWORD` (ig-login only), `INSTAGRAM_DATA_DIR`, `INSTAGRAM_COOKIES_FILE`, `MAX_UPLOAD_MB`, `MAX_PARALLEL_DOWNLOADS`.
