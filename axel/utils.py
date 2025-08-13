import re

ANSI_ESCAPE_RE = re.compile(
    "\x1B\\[[0-?]*[ -/]*[@-~]"  # CSI sequences
    "|\x1B\\][^\x07\x1B]*(?:\x07|\x1B\\\\)"  # OSC sequences
)


def strip_ansi(text: str | bytes) -> str:
    """Return *text* with ANSI escape sequences removed.

    ``text`` may be a :class:`str` or :class:`bytes` instance. When ``bytes``
    are provided they are decoded as UTF-8 with ``errors='ignore'`` before
    stripping the ANSI sequences.

    Removes color codes, cursor-control sequences, and operating system
    commands, making it useful when capturing CLI output in tests.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8", "ignore")
    return ANSI_ESCAPE_RE.sub("", text)
