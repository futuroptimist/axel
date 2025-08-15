import re

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str | bytes | bytearray | None) -> str:
    """Return *text* with ANSI escape sequences removed.

    Args:
        text: Text to clean. ``None`` returns an empty string.

    ``text`` may be a :class:`str`, :class:`bytes` or :class:`bytearray`
    instance. When bytes-like objects are provided they are decoded as UTF-8
    with ``errors='ignore'`` before stripping the ANSI sequences. Passing any
    other type raises ``TypeError``.

    Removes color codes and other cursor-control sequences, making it useful
    when capturing CLI output in tests.
    """
    if text is None:
        return ""
    if isinstance(text, (bytes, bytearray)):
        text = bytes(text).decode("utf-8", "ignore")
    elif not isinstance(text, str):
        raise TypeError("text must be str, bytes, bytearray, or None")
    return ANSI_ESCAPE_RE.sub("", text)
