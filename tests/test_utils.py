from axel import strip_ansi


def test_strip_ansi_removes_codes():
    colored = "\x1b[31merror\x1b[0m"
    assert strip_ansi(colored) == "error"


def test_strip_ansi_handles_cursor_codes() -> None:
    """Non-color ANSI sequences should also be stripped."""
    text = "\x1b[2Kerror"
    assert strip_ansi(text) == "error"


def test_strip_ansi_strips_osc_sequences() -> None:
    """OSC hyperlinks must be removed."""
    text = "\x1b]8;;https://example.com\x1b\\link\x1b]8;;\x1b\\"
    assert strip_ansi(text) == "link"


def test_strip_ansi_accepts_bytes() -> None:
    """Byte strings should also be handled."""
    assert strip_ansi(b"\x1b[31merror\x1b[0m") == "error"


def test_strip_ansi_none_returns_empty() -> None:
    """Passing ``None`` should return an empty string."""
    assert strip_ansi(None) == ""
