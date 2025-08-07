import importlib
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_add_repo_strips_whitespace(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo\n", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_add_repo_creates_parent_dir(tmp_path: Path) -> None:
    file = tmp_path / "nested" / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    assert file.read_text() == "https://example.com/repo\n"


def test_remove_repo_missing(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    remove_repo("https://example.com/other", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_remove_repo_strips_whitespace(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    remove_repo("https://example.com/repo \n", path=file)
    assert load_repos(path=file) == []


def test_env_default_var(monkeypatch, tmp_path: Path):
    repo_file = tmp_path / "repos.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    import axel.repo_manager as rm

    importlib.reload(rm)
    rm.add_repo("https://example.com/repo")
    assert repo_file.read_text().strip() == "https://example.com/repo"


def test_env_dynamic_at_runtime(monkeypatch, tmp_path: Path) -> None:
    """``AXEL_REPO_FILE`` is honored without reloading the module."""
    repo_file = tmp_path / "repos_runtime.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    import axel.repo_manager as rm

    rm.add_repo("https://example.com/runtime")
    assert repo_file.read_text().strip() == "https://example.com/runtime"


def test_remove_repo_leaves_newline(tmp_path: Path) -> None:
    """Line 38 in remove_repo appends a trailing newline when repos remain."""
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo1", path=file)
    add_repo("https://example.com/repo2", path=file)
    remove_repo("https://example.com/repo1", path=file)
    assert file.read_text() == "https://example.com/repo2\n"


def test_cli_add_and_list_direct(tmp_path: Path, capsys) -> None:
    """Call ``main`` directly to include CLI logic in coverage metrics."""
    from axel import repo_manager as rm

    file = tmp_path / "repos.txt"
    rm.main(["--path", str(file), "add", "https://example.com/repo"])  # add
    output = capsys.readouterr().out.strip()
    assert output == "https://example.com/repo"

    rm.main(["--path", str(file), "list"])  # list
    output = capsys.readouterr().out.strip()
    assert output == "https://example.com/repo"


def test_cli_default_lists(tmp_path: Path, capsys) -> None:
    """When no subcommand is provided the repo list is printed."""
    from axel import repo_manager as rm

    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    rm.main(["--path", str(file)])
    assert capsys.readouterr().out.strip() == "https://example.com/repo"


def test_cli_remove_direct(tmp_path: Path, capsys) -> None:
    """Direct call of ``main`` covers the ``remove`` branch."""
    from axel import repo_manager as rm

    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    rm.main(["--path", str(file), "remove", "https://example.com/repo"])  # remove
    assert capsys.readouterr().out.strip() == ""
    assert not file.read_text()


def test_cli_honors_env_var(monkeypatch, tmp_path: Path, capsys) -> None:
    """CLI uses ``AXEL_REPO_FILE`` when ``--path`` is omitted."""
    repo_file = tmp_path / "repos.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    from axel import repo_manager as rm

    rm.main(["add", "https://example.com/env-cli"])
    assert capsys.readouterr().out.strip() == "https://example.com/env-cli"

    rm.main(["list"])
    assert capsys.readouterr().out.strip() == "https://example.com/env-cli"


def test_load_repos_defaults(monkeypatch, tmp_path: Path) -> None:
    """When no path is provided ``AXEL_REPO_FILE`` is used."""
    repo_file = tmp_path / "repos.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    import axel.repo_manager as rm

    assert rm.load_repos() == []  # file doesn't exist yet
    rm.add_repo("https://example.com/repo")  # default path
    assert rm.load_repos() == ["https://example.com/repo"]


def test_remove_repo_defaults(monkeypatch, tmp_path: Path) -> None:
    """``remove_repo`` should also honor ``AXEL_REPO_FILE``."""
    repo_file = tmp_path / "repos.txt"
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    import axel.repo_manager as rm

    rm.add_repo("https://example.com/repo")
    rm.remove_repo("https://example.com/repo")
    assert rm.load_repos() == []


def test_fetch_repos_cli(monkeypatch, tmp_path: Path, capsys) -> None:
    """``fetch`` replaces the file with GitHub repositories."""
    repo_file = tmp_path / "repos.txt"
    from axel import repo_manager as rm

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    def fake_get(url, headers=None, params=None, timeout=10):
        if params["page"] == 1:
            return FakeResponse(
                [
                    {"html_url": "https://github.com/example/repo1"},
                    {"html_url": "https://github.com/example/repo2"},
                ]
            )
        return FakeResponse([])

    repo_file.write_text("https://old/repo\n")
    monkeypatch.setenv("GH_TOKEN", "token123")
    monkeypatch.setattr(rm.requests, "get", fake_get)

    rm.main(["--path", str(repo_file), "fetch"])

    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        "https://github.com/example/repo1",
        "https://github.com/example/repo2",
    ]
    assert repo_file.read_text() == (
        "https://github.com/example/repo1\nhttps://github.com/example/repo2\n"
    )


def test_fetch_repos_requires_token(monkeypatch, tmp_path: Path) -> None:
    repo_file = tmp_path / "repos.txt"
    from axel import repo_manager as rm

    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        rm.fetch_repos(path=repo_file)
