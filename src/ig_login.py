"""Log in to Instagram from this machine and save the session for the bot.

Run it on the server (over SSH) so Instagram sees the login coming from the
same IP the bot downloads from:

    make ig-login          # log in (asks for 2FA code if needed)
    make ig-check          # verify the saved session still works
"""

import argparse
import getpass
import re
import sys

import instaloader
from instaloader.exceptions import (
    BadCredentialsException,
    LoginException,
    TwoFactorAuthRequiredException,
)

import config
import instagram_session


def _new_loader() -> instaloader.Instaloader:
    return instaloader.Instaloader(
        user_agent=instagram_session.user_agent(), iphone_support=False, quiet=True
    )


CHECKPOINT_PATH = re.compile(r"(/(?:auth_platform|challenge|accounts)/\S*?)(?:\s+-\s+|\s*$)")
CHECKPOINT_ATTEMPTS = 3


def checkpoint_url(error: str) -> str | None:
    """Turn instaloader's relative checkpoint path into a full instagram.com URL."""
    match = CHECKPOINT_PATH.search(error)
    return f"https://www.instagram.com{match.group(1)}" if match else None


def _two_factor(loader: instaloader.Instaloader) -> bool:
    for _ in range(3):
        code = input("2FA code: ").strip()
        try:
            loader.two_factor_login(code)
            return True
        except BadCredentialsException as e:
            print(f"Wrong code: {e}")
    return False


def login(username: str, password: str) -> int:
    # The same loader is reused across retries: its cookies identify the pending
    # checkpoint, so approving it and retrying here lets the login through.
    # Starting a new process would trigger a brand-new checkpoint.
    loader = _new_loader()
    for attempt in range(1, CHECKPOINT_ATTEMPTS + 1):
        try:
            loader.login(username, password)
            break
        except TwoFactorAuthRequiredException:
            if not _two_factor(loader):
                return 1
            break
        except BadCredentialsException as e:
            print(f"Bad credentials: {e}")
            return 1
        except LoginException as e:
            error = str(e)
            if "checkpoint" not in error.lower() and "challenge" not in error.lower():
                print(f"Login failed: {error}")
                return 1
            url = checkpoint_url(error)
            print(
                "\nInstagram wants to confirm this login (checkpoint).\n"
                "Do ONE of these, then come back here:\n"
                f"  a) Open this link in a browser logged into @{username}:\n     {url or error}\n"
                "  b) Open the Instagram app > notifications / 'Was this you?' and tap 'This was me'.\n"
                "If neither shows a prompt, use the SSH-tunnel browser login from the README."
            )
            if attempt == CHECKPOINT_ATTEMPTS:
                return 1
            input(f"\nPress Enter once approved to retry ({attempt}/{CHECKPOINT_ATTEMPTS - 1})...")

    instagram_session.save_session(loader.save_session(), instagram_session.user_agent())
    print(f"Logged in as {username}. Session saved to {config.INSTAGRAM_DATA_DIR}")
    return 0


def check() -> int:
    cookies = instagram_session.cookies_file()
    if not cookies:
        print(f"No session at {config.INSTAGRAM_COOKIES_FILE}. Run `make ig-login`.")
        return 1
    session = instagram_session.read_cookies(cookies)
    if "sessionid" not in session or "csrftoken" not in session:
        print("cookies.txt has no sessionid/csrftoken: not a logged-in session.")
        return 1
    loader = _new_loader()
    loader.load_session(config.INSTAGRAM_USERNAME or "instagram", session)
    user = loader.test_login()
    if not user:
        print("Session is expired or invalid. Run `make ig-login`.")
        return 1
    print(f"Session OK, logged in as {user}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify the saved session")
    parser.add_argument("--username", default=config.INSTAGRAM_USERNAME)
    args = parser.parse_args()

    if args.check:
        return check()
    username = args.username or input("Instagram username: ").strip()
    password = config.INSTAGRAM_PASSWORD or getpass.getpass("Instagram password: ")
    return login(username, password)


if __name__ == "__main__":
    sys.exit(main())
