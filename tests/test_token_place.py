"""Tests for token.place integration helpers."""

from __future__ import annotations

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
