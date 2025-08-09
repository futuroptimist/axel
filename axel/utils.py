import re

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    """Return *text* with ANSI escape sequences removed.

    Removes color codes and other cursor-control sequences, making it
    useful when capturing CLI output in tests.
    """
    return ANSI_ESCAPE_RE.sub("", text)
