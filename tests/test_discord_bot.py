import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import axel.discord_bot as db  # noqa: E402


class DummyAuthor:
    display_name = "user"


class DummyMessage:
    def __init__(self, content: str, mid: int = 1) -> None:
        self.content = content
        self.id = mid
        self.author = DummyAuthor()


def test_save_message(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("hello")
    path = db.save_message(msg)
    assert path.read_text() == "# user\n\nhello\n"
