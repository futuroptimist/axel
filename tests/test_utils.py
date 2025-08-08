from axel.utils import strip_ansi


def test_strip_ansi_removes_codes():
    colored = "\x1b[31merror\x1b[0m"
    assert strip_ansi(colored) == "error"
