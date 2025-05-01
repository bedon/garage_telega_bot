# Social Media Video Downloader Bot

A Telegram bot that automatically downloads and forwards videos from various social media platforms (Instagram, Facebook, Twitter, TikTok) to your chat.

## Features

- Downloads videos from Instagram, Facebook, Twitter, and TikTok
- Automatically forwards videos to the chat
- Deletes original messages after successful download
- Provides alternative download links if automatic download fails
- Customizable user status messages
- Automatic handler discovery and loading

### System Dependencies

FFmpeg is required for video processing. Install it using one of the following commands based on your operating system:

```bash
# On Ubuntu/Debian
sudo apt-get install ffmpeg

# On CentOS/RHEL
sudo yum install ffmpeg

# On macOS with Homebrew
brew install ffmpeg
```

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd garage_telega_bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and add your Telegram bot token:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   ```

5. Run the bot:
```bash
python src/main.py
```

## Environment Variables

The bot uses the following environment variables:

- `TELEGRAM_TOKEN`: Your Telegram bot token (required)
  - Get it from [@BotFather](https://t.me/BotFather) on Telegram
  - This token is used to authenticate your bot with the Telegram API
  - Keep this token secure and never share it publicly

## Creating Custom Handlers

You can add support for additional social media platforms by creating new handler classes. The bot automatically discovers and loads all handlers from the `src/handlers` directory. Here's how to create a new handler:

1. Create a new file in `src/handlers/` (e.g., `youtube_handler.py`)
2. Implement the handler class following this template:

```python
from telegram import Update
from utils import delete_message

class YouTubeHandler:
    def __init__(self):
        # Define URL patterns that this handler can process
        self.YOUTUBE_LINKS = ["https://youtube.com/", "https://youtu.be/"]

    def can_handle(self, message: str) -> bool:
        # Check if the message contains any of the defined URL patterns
        return any(link in message for link in self.YOUTUBE_LINKS)

    async def handle(self, update: Update, message: str, sender_name: str) -> None:
        try:
            # Your video download and processing logic here
            youtube_link = f'<a href="{message}">📺 From YouTube</a>'
            
            # Example: Download and send video
            await update.message.chat.send_video(
                video=video_url,
                caption=f"{sender_name} {youtube_link}",
                parse_mode="HTML"
            )
            await delete_message(update)
            
        except Exception as e:
            print(f"Error processing YouTube video: {e}")
            # Handle errors appropriately
```

3. The handler will be automatically loaded when the bot starts. No need to modify any other files!

### Handler Naming Convention

- Handler class names must end with `Handler` (e.g., `YouTubeHandler`, `InstagramHandler`)
- The file name should match the class name in lowercase with underscores (e.g., `youtube_handler.py` for `YouTubeHandler`)

## Handler Development Guidelines

1. **URL Pattern Matching**:
   - Define clear URL patterns in the `__init__` method
   - Use `can_handle()` to check if the handler can process the message

2. **Error Handling**:
   - Implement proper error handling in the `handle()` method
   - Provide fallback options or alternative download links
   - Log errors for debugging

3. **Message Formatting**:
   - Use HTML formatting for links and captions
   - Include the sender's name and platform icon in the caption
   - Delete the original message after successful processing

4. **Resource Management**:
   - Clean up temporary files after use
   - Handle memory efficiently when processing large files
   - Implement timeouts for external API calls

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
