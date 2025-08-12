from axel import strip_ansi


def test_strip_ansi_removes_codes():
    colored = "\x1b[31merror\x1b[0m"
    assert strip_ansi(colored) == "error"


def test_strip_ansi_handles_cursor_codes() -> None:
    """Non-color ANSI sequences should also be stripped."""
    text = "\x1b[2Kerror"
    assert strip_ansi(text) == "error"


def test_strip_ansi_accepts_bytes() -> None:
    """Byte strings should also be handled."""
    assert strip_ansi(b"\x1b[31merror\x1b[0m") == "error"
