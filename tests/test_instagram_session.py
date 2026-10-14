import config
import instagram_session


def test_cookies_round_trip(tmp_path):
    path = tmp_path / "cookies.txt"
    instagram_session.write_cookies({"sessionid": "abc", "csrftoken": "tok"}, path)
    assert path.read_text().startswith("# Netscape HTTP Cookie File")
    assert instagram_session.read_cookies(path) == {"sessionid": "abc", "csrftoken": "tok"}


def test_read_cookies_handles_browser_export(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\n"
        "#HttpOnly_.instagram.com\tTRUE\t/\tTRUE\t1999999999\tsessionid\tsecret\n"
        ".instagram.com\tTRUE\t/\tTRUE\t1999999999\tcsrftoken\ttok\n"
        ".facebook.com\tTRUE\t/\tTRUE\t1999999999\tc_user\tother\n"
    )
    assert instagram_session.read_cookies(path) == {"sessionid": "secret", "csrftoken": "tok"}


def test_user_agent_defaults_and_reads_file(instagram_data_dir):
    assert instagram_session.user_agent() == config.DEFAULT_USER_AGENT
    instagram_session.save_session({"sessionid": "x"}, "Custom UA")
    assert instagram_session.user_agent() == "Custom UA"
    assert instagram_session.cookies_file() == config.INSTAGRAM_COOKIES_FILE


def test_cookies_file_missing():
    assert instagram_session.cookies_file() is None
