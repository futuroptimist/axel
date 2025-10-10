"""Tests for token.place integration helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import axel.token_place as token_place


@pytest.fixture(autouse=True)
def _reset_model_cache() -> None:
    """Ensure cached model metadata does not leak between tests."""

    token_place._clear_model_cache()
    yield
    token_place._clear_model_cache()


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


def test_rotate_api_keys_requests_new_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rotating keys posts to the auth endpoint and returns secrets."""

    captured: dict[str, object] = {}

    def fake_post(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse(
            data={"data": {"relay_key": "relay-new", "server_key": "server-new"}}
        )

    monkeypatch.setattr(token_place.requests, "post", fake_post)

    result = token_place.rotate_api_keys(
        base_url="https://token.place/api/v1", api_key="secret", timeout=15
    )

    assert captured["url"] == "https://token.place/api/v1/auth/rotate"
    headers = captured["headers"]
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Accept"] == "application/json"
    assert captured["timeout"] == 15
    assert result == {"relay": "relay-new", "server": "server-new"}


def test_rotate_api_keys_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """An API key is mandatory when rotating credentials."""

    monkeypatch.delenv("TOKEN_PLACE_API_KEY", raising=False)

    with pytest.raises(token_place.TokenPlaceError):
        token_place.rotate_api_keys(base_url="https://token.place/api/v1")


def test_extract_rotated_keys_handles_nested_payloads() -> None:
    """Nested containers and alias fields should collapse into canonical keys."""

    shared = {"relay": "  relay-primary  "}
    payload = {
        "server_token": "  server-root  ",
        "data": [
            shared,
            shared,  # duplicate object to exercise cycle detection
            {
                "keys": [
                    {"relayToken": " relay-secondary "},
                    {"server_key": " server-new "},
                ]
            },
            [
                {"relay_key": " relay-tertiary "},
            ],
        ],
    }

    secrets = token_place._extract_rotated_keys(payload)

    assert secrets == {"relay": "relay-primary", "server": "server-root"}


def test_rotate_api_keys_errors_when_no_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rotation failures surface when the response omits refreshed credentials."""

    def fake_post(
        url: str, headers: dict[str, str], timeout: int
    ) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(data={"data": {"message": "ok"}})

    monkeypatch.setattr(token_place.requests, "post", fake_post)

    with pytest.raises(
        token_place.TokenPlaceError, match="did not include rotated keys"
    ):
        token_place.rotate_api_keys(
            base_url="https://token.place/api/v1", api_key="secret", timeout=10
        )


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


def test_main_rotate_prints_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The rotate subcommand should display refreshed credentials."""

    monkeypatch.setattr(
        token_place,
        "rotate_api_keys",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: {
            "relay": "relay-new",
            "server": "server-new",
        },
    )

    token_place.main(
        [
            "rotate",
            "--base-url",
            "https://token.place/api/v1",
            "--api-key",
            "secret",
        ]
    )

    output = capsys.readouterr().out.strip().splitlines()
    assert output[0].startswith("Rotated token.place keys:")
    assert "- relay: relay-new" in output
    assert "- server: server-new" in output


def test_main_rotate_reports_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rotation failures exit with a helpful message."""

    def boom(**_: object) -> dict[str, str]:  # pragma: no cover - helper
        raise token_place.TokenPlaceError("denied")

    monkeypatch.setattr(token_place, "rotate_api_keys", boom)

    with pytest.raises(SystemExit) as excinfo:
        token_place.main(["rotate"])

    assert excinfo.value.code == 1
    assert "denied" in capsys.readouterr().err


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


def test_main_defaults_to_list_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invoking the CLI with no argv defaults to the list subcommand."""

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "gamma"
        ],
    )
    monkeypatch.setattr(sys, "argv", ["token_place"])

    token_place.main()

    output = capsys.readouterr().out.strip().splitlines()
    assert output[0] == "Available models:"
    assert output[1] == "- gamma"


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


def test_plan_client_integrations_reuses_model_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Model metadata is fetched once per token.place configuration."""

    calls: list[tuple[str | None, str | None]] = []

    def fake_list_models(
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = token_place.DEFAULT_TIMEOUT,
    ) -> list[str]:  # pragma: no cover - helper
        calls.append((base_url, api_key))
        return ["model-a"]

    token_place._clear_model_cache()
    monkeypatch.setattr(token_place, "list_models", fake_list_models)

    repos = [
        "https://github.com/example/token.place",
        "https://github.com/example/alpha",
        "https://github.com/example/beta",
    ]

    token_place.plan_client_integrations(
        repos, base_url="https://token.place/api/v1", api_key="secret"
    )

    assert len(calls) == 1
    assert calls[0] == ("https://token.place/api/v1", "secret")
    token_place._clear_model_cache()


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
