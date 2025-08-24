import re

ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1B(?:
        \[[0-?]*[ -/]*[@-~]      # CSI sequences
      | \][^\x1B\x07]*(?:\x07|\x1B\\)  # OSC sequences
    )
    """,
    re.VERBOSE,
)


def strip_ansi(text: str | bytes | bytearray | memoryview | None) -> str:
    """Return *text* with ANSI escape sequences removed.

    Args:
        text: Text to clean. ``None`` returns an empty string.

    ``text`` may be a :class:`str`, :class:`bytes`, :class:`bytearray` or
    :class:`memoryview` instance. When bytes-like objects are provided they are
    decoded as UTF-8 with ``errors='ignore'`` before stripping the ANSI
    sequences. Passing any other type raises ``TypeError``.

    Removes color codes, cursor-control sequences, and OSC commands, making it
    useful when capturing CLI output in tests.
    """
    if text is None:
        return ""
    if isinstance(text, (bytes, bytearray, memoryview)):
        text = bytes(text).decode("utf-8", "ignore")
    elif not isinstance(text, str):
        raise TypeError("text must be str, bytes, bytearray, memoryview, or None")
    return ANSI_ESCAPE_RE.sub("", text)
