import re

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Return *text* with ANSI escape codes removed.

    Useful when capturing colored CLI output in tests.
    """
    return ANSI_ESCAPE_RE.sub("", text)
