# Garage Telega Bot

## Project Overview
Python Telegram bot that automatically downloads videos from social media platforms (Instagram, Facebook, Twitter, TikTok) and forwards them to chat with original message deletion.

## Architecture
- **Main**: `src/main.py` - Bot initialization and message routing
- **Handlers**: `src/handlers/` - Platform-specific download handlers (auto-discovered)
- **Utils**: `src/utils.py` - Shared utilities (status randomization, handler loading, message deletion)

## Key Technologies
- `python-telegram-bot==22.0` - Telegram API
- `yt-dlp>=2025.3.31` - Video downloading
- `aiohttp==3.11.18` - HTTP requests
- `instaloader>=4.10.0` - Instagram content
- `ffmpeg` - Video processing (system dependency)

## Handler Pattern
Each platform handler implements:
- `can_handle(message)` - URL pattern matching
- `handle(update, message, sender_name)` - Download and forward logic
- Auto-discovery from `src/handlers/` directory

## Testing
- `pytest` with async support
- Coverage reporting available
- Tests in `tests/` directory

## Environment
- `TELEGRAM_TOKEN` - Bot authentication (required)
- `.env` file for configuration