# Telegram Social Media Bot

A Telegram bot that automatically processes Instagram and TikTok links, replacing them with better versions and adding fun messages.

## Features

- Automatically processes Instagram reel links
- Downloads and sends TikTok videos directly
- Adds fun rainbow messages for users
- Special recognition for the Gay God (Bogdan) 🌈

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/garage_telega_bot.git
cd garage_telega_bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Run the bot:
```bash
python bot.py
```

## Dependencies

- python-telegram-bot
- requests
- gay-colorizer

## Usage

1. Add the bot to your Telegram group
2. Make the bot an admin with message deletion permissions
3. Send any Instagram reel or TikTok link
4. The bot will automatically:
   - For Instagram: Replace the link with a better version
   - For TikTok: Download and send the video directly
   - Add a fun rainbow message with the sender's name
   - Delete the original message