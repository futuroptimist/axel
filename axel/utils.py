import re

ANSI_ESCAPE_RE = re.compile(
    r"""
    \x1B  # ESC
    (
        \[[0-?]*[ -/]*[@-~]        # CSI sequences
        |
        \].*?(?:\x07|\x1B\\)    # OSC sequences, terminated by BEL or ESC\\
    )
    """,
    re.VERBOSE,
)


def strip_ansi(text: str | bytes | None) -> str:
    """Return *text* with ANSI escape sequences removed.

    Args:
        text: Text to clean. ``None`` returns an empty string.

    ``text`` may be a :class:`str` or :class:`bytes` instance. When ``bytes``
    are provided they are decoded as UTF-8 with ``errors='ignore'`` before
    stripping the ANSI sequences.

    Removes color, cursor-control, and OSC hyperlink sequences, making it
    useful when capturing CLI output in tests.
    """
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "ignore")
    return ANSI_ESCAPE_RE.sub("", text)
