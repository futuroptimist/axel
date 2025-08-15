from axel import strip_ansi


def test_strip_ansi_accepts_bytearray() -> None:
    """Bytearray inputs should also be handled."""
    assert strip_ansi(bytearray(b"\x1b[31merror\x1b[0m")) == "error"
