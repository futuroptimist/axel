import importlib
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
import pytest  # noqa: E402
import requests  # noqa: E402

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


def test_main_add_accepts_path_after_subcommand(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from axel.repo_manager import main

    file = tmp_path / "repos.txt"

    main(
        [
            "add",
            "https://example.com/repo",
            "--path",
            str(file),
        ]
    )

    assert load_repos(path=file) == ["https://example.com/repo"]
    assert "https://example.com/repo" in capsys.readouterr().out


def test_main_add_uses_default_repo_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import repo_manager

    default_file = tmp_path / "repos.txt"
    monkeypatch.setattr(repo_manager, "get_repo_file", lambda: default_file)

    repo_manager.main(["add", "https://example.com/repo"])

    assert load_repos(path=default_file) == ["https://example.com/repo"]


def test_main_add_supports_path_equals_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import repo_manager

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    target = Path("~") / "nested" / "repos.txt"

    repo_manager.main(
        [
            "add",
            "https://example.com/repo",
            f"--path={target}",
        ]
    )

    expected_file = home / "nested" / "repos.txt"
    assert load_repos(path=expected_file) == ["https://example.com/repo"]


def test_main_add_accepts_path_before_subcommand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import repo_manager

    class SneakyStr(str):
        def __eq__(self, other: object) -> bool:
            return False

        __hash__ = str.__hash__

    file = tmp_path / "repos.txt"
    argv = [
        SneakyStr("--path"),
        str(file),
        "add",
        "https://example.com/repo",
    ]

    repo_manager.main(argv)

    assert load_repos(path=file) == ["https://example.com/repo"]


def test_main_uses_sys_argv_when_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import types

    from axel import repo_manager

    file = tmp_path / "repos.txt"

    monkeypatch.setattr(
        repo_manager,
        "sys",
        types.SimpleNamespace(
            argv=[
                "prog",
                "add",
                "https://example.com/repo",
                "--path",
                str(file),
            ]
        ),
    )

    repo_manager.main(None)

    assert load_repos(path=file) == ["https://example.com/repo"]


def test_main_rejects_path_without_value() -> None:
    from axel.repo_manager import main

    with pytest.raises(SystemExit) as excinfo:
        main(["add", "https://example.com/repo", "--path"])

    assert excinfo.value.code != 0


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


def test_load_repos_auto_fetches_when_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing repo files trigger an automatic fetch when opt-in is set."""

    collected: dict[str, Path | None] = {"path": None}

    def fake_fetch_repos(*, path: Path | None = None, **_: object) -> list[str]:
        collected["path"] = path
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("https://example.com/axel\n", encoding="utf-8")
        return ["https://example.com/axel"]

    repo_file = tmp_path / "repos.txt"

    monkeypatch.setenv("AXEL_AUTO_FETCH_REPOS", "1")
    monkeypatch.setattr("axel.repo_manager.fetch_repos", fake_fetch_repos)

    from axel import repo_manager as rm

    repos = rm.load_repos(path=repo_file)

    assert repos == ["https://example.com/axel"]
    assert collected["path"] == repo_file


def test_load_repos_auto_fetch_handles_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Auto fetch falls back to an empty list when fetching fails."""

    def fake_fetch_repos(*, path: Path | None = None, **_: object) -> list[str]:
        raise RuntimeError("credentials required")

    repo_file = tmp_path / "repos.txt"

    monkeypatch.setenv("AXEL_AUTO_FETCH_REPOS", "1")
    monkeypatch.setattr("axel.repo_manager.fetch_repos", fake_fetch_repos)

    from axel import repo_manager as rm

    repos = rm.load_repos(path=repo_file)

    assert repos == []
    assert not repo_file.exists()


def test_load_repos_ignores_comments(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    file.write_text(
        "https://example.com/a\n"
        "# comment line\n"
        "https://example.com/b # trailing comment\n"
    )
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_load_repos_strips_trailing_slash(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    file.write_text("https://example.com/repo/\n")
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_load_repos_deduplicates(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    file.write_text(
        "https://example.com/a\n" "https://example.com/a\n" "https://example.com/b\n"
    )
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_load_repos_sorts_entries(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    file.write_text("https://example.com/b\nhttps://example.com/a\n")
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_add_repo_expands_user_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    file = Path("~/repos.txt")
    add_repo("https://example.com/repo", path=file)
    expected = tmp_path / "repos.txt"
    assert expected.exists()
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_add_repo_no_duplicates(tmp_path: Path):
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    add_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_add_repo_no_duplicates_case_insensitive(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/Repo", path=file)
    add_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == ["https://example.com/Repo"]


def test_add_repo_strips_whitespace(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo\n", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_remove_repo_case_insensitive(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/Repo", path=file)
    remove_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == []


def test_add_repo_strips_trailing_slash(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo/", path=file)
    add_repo("https://example.com/repo", path=file)
    assert load_repos(path=file) == ["https://example.com/repo"]


def test_add_repo_keeps_list_sorted(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/b", path=file)
    add_repo("https://example.com/a", path=file)
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_add_repo_sorts_case_insensitively(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/B", path=file)
    add_repo("https://example.com/a", path=file)
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/B",
    ]


def test_add_repo_creates_parent_dir(tmp_path: Path) -> None:
    file = tmp_path / "nested" / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    assert file.read_text() == "https://example.com/repo\n"


def test_add_repo_requires_scheme(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    with pytest.raises(ValueError):
        add_repo("github.com/u/repo", path=file)


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


def test_remove_repo_strips_trailing_slash(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    add_repo("https://example.com/repo", path=file)
    remove_repo("https://example.com/repo/", path=file)
    assert load_repos(path=file) == []


def test_remove_repo_sorts_remaining(tmp_path: Path) -> None:
    file = tmp_path / "repos.txt"
    file.write_text(
        "https://example.com/b\nhttps://example.com/a\nhttps://example.com/c\n"
    )
    remove_repo("https://example.com/c", path=file)
    assert load_repos(path=file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


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


def test_env_var_expands_user(monkeypatch, tmp_path: Path) -> None:
    """``AXEL_REPO_FILE`` supports ``~`` expansion."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AXEL_REPO_FILE", "~/repos.txt")
    import axel.repo_manager as rm

    rm.add_repo("https://example.com/tilde")
    assert rm.get_repo_file() == home / "repos.txt"
    assert (home / "repos.txt").read_text().strip() == "https://example.com/tilde"


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


def test_fetch_repos(monkeypatch, tmp_path: Path) -> None:
    """``fetch_repos`` retrieves repos and writes them to disk."""
    repo_file = tmp_path / "repos.txt"

    def fake_get(url, headers=None, params=None, timeout=0):
        class Resp:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        if params["page"] == 1:
            return Resp(
                [
                    {"html_url": "https://github.com/u/a"},
                    {"html_url": "https://github.com/u/b"},
                ]
            )
        return Resp([])

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    repos = rm.fetch_repos(path=repo_file)
    assert repos == [
        "https://github.com/u/a",
        "https://github.com/u/b",
    ]
    assert repo_file.read_text() == "https://github.com/u/a\nhttps://github.com/u/b\n"


def test_cli_fetch(monkeypatch, tmp_path: Path, capsys) -> None:
    """CLI ``fetch`` writes and prints fetched repositories."""
    repo_file = tmp_path / "repos.txt"

    def fake_get(url, headers=None, params=None, timeout=0):
        class Resp:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        if params["page"] == 1:
            return Resp(
                [
                    {"html_url": "https://github.com/u/a"},
                    {"html_url": "https://github.com/u/b"},
                ]
            )
        return Resp([])

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    rm.main(["--path", str(repo_file), "fetch"])
    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        "https://github.com/u/a",
        "https://github.com/u/b",
    ]
    assert repo_file.read_text() == "https://github.com/u/a\nhttps://github.com/u/b\n"


def test_cli_fetch_accepts_token_flag(monkeypatch, tmp_path: Path, capsys) -> None:
    """Passing ``--token`` bypasses the ``GH_TOKEN``/``GITHUB_TOKEN`` env vars."""
    repo_file = tmp_path / "repos.txt"

    def fake_get(url, headers=None, params=None, timeout=0):
        class Resp:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        if params["page"] == 1:
            return Resp(
                [
                    {"html_url": "https://github.com/u/a"},
                    {"html_url": "https://github.com/u/b"},
                ]
            )
        return Resp([])

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    rm.main(["--path", str(repo_file), "fetch", "--token", "token"])
    output = capsys.readouterr().out.strip().splitlines()
    assert output == [
        "https://github.com/u/a",
        "https://github.com/u/b",
    ]
    assert repo_file.read_text() == "https://github.com/u/a\nhttps://github.com/u/b\n"


def test_cli_fetch_accepts_visibility_flag(monkeypatch, tmp_path: Path) -> None:
    """``--visibility`` limits repositories returned from GitHub."""
    repo_file = tmp_path / "repos.txt"
    captured: dict[str, str | None] = {}

    def fake_get(url, headers=None, params=None, timeout=0):
        captured["visibility"] = params.get("visibility")

        class Resp:
            def __init__(self):
                self._data = []

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    rm.main(
        [
            "--path",
            str(repo_file),
            "fetch",
            "--token",
            "token",
            "--visibility",
            "public",
        ]
    )
    assert captured["visibility"] == "public"


def test_fetch_repo_urls_requires_token(monkeypatch) -> None:
    """Fetching without ``GH_TOKEN``/``GITHUB_TOKEN`` raises an error."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    from axel import repo_manager as rm

    with pytest.raises(RuntimeError):
        rm.fetch_repo_urls()


def test_fetch_repo_urls_uses_github_token(monkeypatch) -> None:
    """``GITHUB_TOKEN`` is accepted when ``GH_TOKEN`` is missing."""

    def fake_get(url, headers=None, params=None, timeout=0):
        class Resp:
            def __init__(self):
                self._data = []

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    assert rm.fetch_repo_urls() == []


def test_fetch_repo_urls_accepts_visibility(monkeypatch) -> None:
    """The optional ``visibility`` parameter is passed to the API."""
    captured: dict[str, str | None] = {}

    def fake_get(url, headers=None, params=None, timeout=0):
        captured["visibility"] = params.get("visibility")

        class Resp:
            def __init__(self):
                self._data = []

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    rm.fetch_repo_urls(visibility="private")
    assert captured["visibility"] == "private"


def test_fetch_repo_urls_deduplicates_case_insensitive(monkeypatch) -> None:
    """Duplicate repositories from the API are removed case-insensitively."""

    pages: dict[int, list[dict[str, str]]] = {
        1: [
            {"html_url": "https://github.com/example/Axel"},
            {"html_url": "https://github.com/example/axel"},
        ],
        2: [],
    }

    def fake_get(url, headers=None, params=None, timeout=0):
        page = params.get("page", 1)

        class Resp:
            def __init__(self, data: list[dict[str, str]]):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        return Resp(pages.get(page, []))

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    repos = rm.fetch_repo_urls()

    assert repos == ["https://github.com/example/Axel"]


def test_fetch_repo_urls_skips_invalid_entries(monkeypatch) -> None:
    """Entries without usable URLs are ignored."""

    responses: dict[int, list[dict[str, object]]] = {
        1: [
            {"html_url": "https://github.com/example/valid"},
            {"html_url": None},
            {"html_url": "   /"},
        ],
        2: [],
    }

    def fake_get(url, headers=None, params=None, timeout=0):
        page = params.get("page", 1)

        class Resp:
            def __init__(self, data: list[dict[str, object]]):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        return Resp(responses.get(page, []))

    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    repos = rm.fetch_repo_urls()

    assert repos == ["https://github.com/example/valid"]


def test_fetch_repos_defaults(monkeypatch, tmp_path: Path) -> None:
    """``fetch_repos`` honors ``AXEL_REPO_FILE`` when no path is given."""
    repo_file = tmp_path / "repos.txt"

    def fake_get(url, headers=None, params=None, timeout=0):
        class Resp:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            def raise_for_status(self):
                return None

        if params["page"] == 1:
            return Resp([{"html_url": "https://github.com/u/a"}])
        return Resp([])

    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(requests, "get", fake_get)
    from axel import repo_manager as rm

    rm.fetch_repos()
    assert repo_file.read_text() == "https://github.com/u/a\n"
