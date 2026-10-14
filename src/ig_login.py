"""Log in to Instagram from this machine and save the session for the bot.

Run it on the server (over SSH) so Instagram sees the login coming from the
same IP the bot downloads from:

    make ig-login          # log in (asks for 2FA code if needed)
    make ig-check          # verify the saved session still works
"""

import argparse
import getpass
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


def login(username: str, password: str) -> int:
    loader = _new_loader()
    try:
        loader.login(username, password)
    except TwoFactorAuthRequiredException:
        for _ in range(3):
            code = input("2FA code: ").strip()
            try:
                loader.two_factor_login(code)
                break
            except BadCredentialsException as e:
                print(f"Wrong code: {e}")
        else:
            return 1
    except BadCredentialsException as e:
        print(f"Bad credentials: {e}")
        return 1
    except LoginException as e:
        print(f"Login failed: {e}")
        if "checkpoint" in str(e).lower() or "challenge" in str(e).lower():
            print(
                "\nInstagram wants to confirm this login. Open the Instagram app "
                "(or instagram.com) on your phone, approve the login from the "
                "new location ('This was me'), then run this command again."
            )
        return 1

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
