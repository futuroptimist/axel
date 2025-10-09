"""Helpers for integrating with the token.place API."""

from __future__ import annotations

import os
from typing import Iterable, Sequence
from urllib.parse import urljoin

import requests

DEFAULT_API_URL = "http://localhost:5000/api/v1"
DEFAULT_TIMEOUT = 10
_PREVIEW_PREFERENCE: tuple[str, ...] = (
    "llama-3-8b-instruct:alignment",
    "llama-3-8b-instruct",
)


class TokenPlaceError(RuntimeError):
    """Raised when the token.place API cannot satisfy a request."""


def _resolve_base_url(base_url: str | None) -> str:
    url = base_url or os.getenv("AXEL_TOKEN_PLACE_URL") or DEFAULT_API_URL
    return url.rstrip("/")


def _resolve_api_key(api_key: str | None) -> str | None:
    key = api_key if api_key is not None else os.getenv("TOKEN_PLACE_API_KEY")
    if not key:
        return None
    cleaned = key.strip()
    return cleaned or None


def _extract_model_ids(payload: object) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()

    def _append(model_id: str) -> None:
        if model_id and model_id not in seen:
            seen.add(model_id)
            models.append(model_id)

    items: Iterable[object] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            items = payload["data"]  # type: ignore[assignment]
        elif isinstance(payload.get("models"), list):
            items = payload["models"]  # type: ignore[assignment]
    elif isinstance(payload, list):
        items = payload

    for item in items:
        if isinstance(item, str):
            _append(item)
        elif isinstance(item, dict):
            for key in ("id", "model", "name"):
                value = item.get(key)
                if isinstance(value, str):
                    _append(value)
                    break
    return models


def list_models(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[str]:
    """Return model identifiers advertised by the token.place API."""

    resolved_url = _resolve_base_url(base_url)
    headers = {"Accept": "application/json"}
    key = _resolve_api_key(api_key)
    if key:
        headers["Authorization"] = f"Bearer {key}"

    url = urljoin(resolved_url + "/", "models")
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - exercised via tests
        raise TokenPlaceError(f"Unable to reach token.place at {url}") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - exercised via tests
        status = getattr(response, "status_code", "unknown")
        raise TokenPlaceError(f"token.place returned HTTP {status} for {url}") from exc

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        raise TokenPlaceError("token.place returned invalid JSON") from exc

    return _extract_model_ids(payload)


def _select_featured_model(models: Sequence[str]) -> str | None:
    for candidate in _PREVIEW_PREFERENCE:
        if candidate in models:
            return candidate
    return models[0] if models else None


def quest_detail(
    primary_slug: str,
    secondary_slug: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> str:
    """Return a quest detail string enriched with token.place models."""

    try:
        models = list_models(base_url=base_url, api_key=api_key)
    except TokenPlaceError:
        models = []

    featured = _select_featured_model(models)
    if featured:
        return (
            f"{primary_slug} can broker token.place auth via {featured} "
            f"while gabriel audits secrets so {secondary_slug} ships safely."
        )
    return (
        f"{primary_slug} can broker token.place auth while gabriel audits secrets "
        f"so {secondary_slug} ships safely."
    )


__all__ = [
    "TokenPlaceError",
    "DEFAULT_API_URL",
    "DEFAULT_TIMEOUT",
    "list_models",
    "quest_detail",
]
