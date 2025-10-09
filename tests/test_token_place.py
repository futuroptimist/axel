"""Tests for token.place integration helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import axel.token_place as token_place


class DummyResponse:
    """Simple stand-in for :mod:`requests` responses."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        data: object | None = None,
        exc: Exception | None = None,
    ):
        self.status_code = status_code
        self._data = data
        self._exc = exc

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise token_place.requests.HTTPError(
                response=SimpleNamespace(status_code=self.status_code)
            )

    def json(self) -> object:
        if self._exc is not None:
            raise self._exc
        return self._data


def test_list_models_parses_openai_like_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``list_models`` returns model IDs from standard OpenAI responses."""

    response = DummyResponse(
        data={
            "data": [
                {"id": "llama-3-8b-instruct"},
                {"id": "llama-3-8b-instruct:alignment"},
            ]
        }
    )

    def fake_get(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        return response

    monkeypatch.setattr(
        token_place.requests,
        "get",
        fake_get,
    )

    models = token_place.list_models(
        base_url="https://token.place/api/v1", api_key=None
    )
    assert models == [
        "llama-3-8b-instruct",
        "llama-3-8b-instruct:alignment",
    ]


def test_main_prints_models(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI entry point should display available models."""

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "alpha",
            "beta",
        ],
    )

    token_place.main(["--base-url", "https://token.place/api/v1"])

    output = capsys.readouterr().out.strip().splitlines()
    assert output[0].startswith("Available models:")
    assert "- alpha" in output
    assert "- beta" in output


def test_main_reports_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Errors surface via a non-zero exit code and stderr message."""

    def boom(**_: object) -> list[str]:  # pragma: no cover - helper
        raise token_place.TokenPlaceError("offline")

    monkeypatch.setattr(token_place, "list_models", boom)

    with pytest.raises(SystemExit) as excinfo:
        token_place.main([])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "offline" in captured.err


def test_main_reports_empty_model_list(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty response prints a helpful message and exits successfully."""

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [],
    )

    token_place.main([])

    captured = capsys.readouterr()
    assert captured.out.strip() == "No models available"


def test_list_models_raises_token_place_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Network failures surface as ``TokenPlaceError`` to the caller."""

    def fake_get(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        raise token_place.requests.RequestException("boom")

    monkeypatch.setattr(
        token_place.requests,
        "get",
        fake_get,
    )

    with pytest.raises(token_place.TokenPlaceError):
        token_place.list_models(base_url="https://token.place/api/v1", api_key=None)


def test_list_models_includes_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API keys are trimmed and forwarded via the Authorization header."""

    captured: dict[str, dict[str, str]] = {}

    def fake_get(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        captured["headers"] = headers
        return DummyResponse(data={"data": []})

    monkeypatch.setattr(
        token_place.requests,
        "get",
        fake_get,
    )

    models = token_place.list_models(
        base_url="https://token.place/api/v1", api_key="  secret  "
    )

    assert models == []
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_list_models_supports_plain_list_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw list payloads are normalised to model IDs."""

    def fake_get(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(data=["model-one", {"name": "model-two"}])

    monkeypatch.setattr(
        token_place.requests,
        "get",
        fake_get,
    )

    models = token_place.list_models(
        base_url="https://token.place/api/v1", api_key=None
    )
    assert models == ["model-one", "model-two"]


def test_list_models_supports_models_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The OpenAI ``models`` key is treated equivalently to ``data``."""

    def fake_get(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(data={"models": [{"model": "alpha"}, "beta"]})

    monkeypatch.setattr(
        token_place.requests,
        "get",
        fake_get,
    )

    models = token_place.list_models(
        base_url="https://token.place/api/v1", api_key=None
    )
    assert models == ["alpha", "beta"]


def test_plan_client_integrations_generates_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Token repos pair with every other repository."""

    captured: list[tuple[str, str, str | None, str | None]] = []

    def fake_detail(
        primary_slug: str,
        secondary_slug: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> str:
        captured.append((primary_slug, secondary_slug, base_url, api_key))
        return f"{primary_slug}->{secondary_slug}"

    monkeypatch.setattr(token_place, "quest_detail", fake_detail)

    repos = [
        "https://github.com/example/token.place",
        "https://github.com/example/alpha",
        "https://github.com/example/beta",
    ]

    integrations = token_place.plan_client_integrations(
        repos, base_url="https://token.place/api/v1", api_key="secret"
    )

    assert [integration.token_repo for integration in integrations] == [
        "example/token.place",
        "example/token.place",
    ]
    assert [integration.client_repo for integration in integrations] == [
        "example/alpha",
        "example/beta",
    ]
    assert [integration.detail for integration in integrations] == [
        "example/token.place->example/alpha",
        "example/token.place->example/beta",
    ]
    assert captured == [
        (
            "example/token.place",
            "example/alpha",
            "https://token.place/api/v1",
            "secret",
        ),
        (
            "example/token.place",
            "example/beta",
            "https://token.place/api/v1",
            "secret",
        ),
    ]


def test_plan_client_integrations_handles_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate or differently cased repos are only paired once."""

    monkeypatch.setattr(
        token_place,
        "quest_detail",
        lambda primary_slug, secondary_slug, **_: f"{primary_slug}->{secondary_slug}",
    )

    repos = [
        "https://github.com/example/token.place",
        "https://github.com/Example/Token.Place",
        "https://github.com/example/alpha",
        "https://github.com/example/ALPHA",
    ]

    integrations = token_place.plan_client_integrations(repos)

    assert [integration.client_repo for integration in integrations] == [
        "example/alpha",
    ]
    assert [integration.detail for integration in integrations] == [
        "example/token.place->example/alpha",
    ]


def test_plan_client_integrations_requires_token_repo() -> None:
    """Without a token.place repository no integrations are produced."""

    repos = ["https://github.com/example/alpha", "https://github.com/example/beta"]

    assert token_place.plan_client_integrations(repos) == []


def test_plan_client_integrations_parses_varied_repos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository URLs with different formats are normalised consistently."""

    monkeypatch.setattr(
        token_place,
        "quest_detail",
        lambda primary_slug, secondary_slug, **_: f"{primary_slug}->{secondary_slug}",
    )

    repos = [
        "https://github.com/example/token.place",
        "https://gitlab.com/example",
        "owner/other-repo",
        "solo",
        "",  # ignored
    ]

    integrations = token_place.plan_client_integrations(repos)

    assert [integration.client_repo for integration in integrations] == [
        "example/example",
        "owner/other-repo",
        "solo",
    ]


def test_main_clients_prints_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI prints integration plans for token.place clients."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/example/token.place\n" "https://github.com/example/alpha\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        token_place,
        "quest_detail",
        lambda primary_slug, secondary_slug, **_: f"{primary_slug}->{secondary_slug}",
    )

    token_place.main(["clients", "--path", str(repo_file)])

    output = capsys.readouterr().out
    assert "example/token.place ↔ example/alpha" in output
    assert "example/token.place->example/alpha" in output


def test_main_clients_reports_missing_token_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI informs the user when no token.place repo exists."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/alpha\n", encoding="utf-8")

    token_place.main(["clients", "--path", str(repo_file)])

    output = capsys.readouterr().out
    assert "No token.place repositories configured" in output
