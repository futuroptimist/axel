from axel import strip_ansi


def test_strip_ansi_accepts_memoryview() -> None:
    """Memoryview inputs should also be handled."""
    assert strip_ansi(memoryview(b"\x1b[31merror\x1b[0m")) == "error"
