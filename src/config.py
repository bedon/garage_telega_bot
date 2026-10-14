import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR").upper()

# Telegram Bot API upload limit is 50 MB.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024

# How many downloads may run at the same time.
MAX_PARALLEL_DOWNLOADS = int(os.getenv("MAX_PARALLEL_DOWNLOADS", "2"))

# Instagram session files written by `make ig-login` (cookies.txt + user_agent.txt).
INSTAGRAM_DATA_DIR = Path(os.getenv("INSTAGRAM_DATA_DIR", PROJECT_ROOT / "data" / "instagram"))
INSTAGRAM_COOKIES_FILE = Path(os.getenv("INSTAGRAM_COOKIES_FILE", INSTAGRAM_DATA_DIR / "cookies.txt"))
INSTAGRAM_USER_AGENT_FILE = INSTAGRAM_DATA_DIR / "user_agent.txt"
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# A single, stable desktop User-Agent. Instagram ties a session to the device it
# was created on, so the same UA must be used for login and every download.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
