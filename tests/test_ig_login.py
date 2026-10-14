from unittest.mock import MagicMock, patch

from instaloader.exceptions import LoginException

import ig_login
import instagram_session

CHECKPOINT_ERROR = (
    "Login: Checkpoint required. Point your browser to /auth_platform/?apc=AdoT-li_fg "
    "- follow the instructions, then retry."
)


def test_checkpoint_url_is_absolute():
    assert ig_login.checkpoint_url(CHECKPOINT_ERROR) == "https://www.instagram.com/auth_platform/?apc=AdoT-li_fg"
    assert ig_login.checkpoint_url("Login: Checkpoint required. /challenge/123/abc/") == \
        "https://www.instagram.com/challenge/123/abc/"
    assert ig_login.checkpoint_url("something else") is None


def test_checkpoint_retries_with_same_loader(capsys):
    loader = MagicMock()
    loader.login.side_effect = [LoginException(CHECKPOINT_ERROR), None]
    loader.save_session.return_value = {"sessionid": "s", "csrftoken": "c"}
    with patch.object(ig_login, "_new_loader", return_value=loader), \
         patch("builtins.input", return_value="") as prompt:
        assert ig_login.login("user", "pw") == 0
    assert loader.login.call_count == 2
    prompt.assert_called_once()
    assert "https://www.instagram.com/auth_platform/?apc=AdoT-li_fg" in capsys.readouterr().out
    assert instagram_session.read_cookies(instagram_session.cookies_file())["sessionid"] == "s"


def test_checkpoint_gives_up_after_attempts():
    loader = MagicMock()
    loader.login.side_effect = LoginException(CHECKPOINT_ERROR)
    with patch.object(ig_login, "_new_loader", return_value=loader), \
         patch("builtins.input", return_value=""):
        assert ig_login.login("user", "pw") == 1
    assert loader.login.call_count == ig_login.CHECKPOINT_ATTEMPTS
    assert instagram_session.cookies_file() is None
