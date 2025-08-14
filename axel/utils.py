import re

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str | bytes | bytearray | None) -> str:
    """Return *text* with ANSI escape sequences removed.

    Args:
        text: Text to clean. ``None`` returns an empty string.

    ``text`` may be a :class:`str`, :class:`bytes`, or :class:`bytearray` instance.
    When bytes-like input is provided it is decoded as UTF-8 with ``errors='ignore'``
    before stripping the ANSI sequences.

    Removes color codes and other cursor-control sequences, making it useful
    when capturing CLI output in tests.
    """
    if text is None:
        return ""
    if isinstance(text, (bytes, bytearray)):
        text = bytes(text).decode("utf-8", "ignore")
    return ANSI_ESCAPE_RE.sub("", text)
