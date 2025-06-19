import sys
from pathlib import Path
import subprocess

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
from axel.repo_manager import add_repo, load_repos, remove_repo  # noqa: E402


def test_add_and_load(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_remove_repo(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    remove_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == []


def test_cli_list_with_path(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    result = subprocess.run(
        [sys.executable, "-m", "axel.repo_manager", "--path", str(file), "list"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert "https://example.com/repo" in result.stdout


def test_cli_remove(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.repo_manager",
            "--path",
            str(file),
            "remove",
            "https://example.com/repo",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )
    assert load_repos(path=file) == []
