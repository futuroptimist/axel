import importlib
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
from axel import add_repo, load_repos, remove_repo  # noqa: E402


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


def test_load_repos_missing_file(tmp_path: Path):
    file = tmp_path / "missing.txt"
    assert load_repos(path=file) == []


def test_add_repo_no_duplicates(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    add_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_remove_repo_missing(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    remove_repo("https://example.com/other", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_env_default_var(monkeypatch, tmp_path: Path):
    repo_file = tmp_path / "repos.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    import axel.repo_manager as rm

    importlib.reload(rm)
    rm.add_repo("https://example.com/repo")
    assert repo_file.read_text().strip() == "https://example.com/repo"
