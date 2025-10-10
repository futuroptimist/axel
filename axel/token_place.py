"""Helpers for integrating with the token.place API."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urljoin, urlparse

import requests

from .repo_manager import get_repo_file, load_repos

DEFAULT_API_URL = "http://localhost:5000/api/v1"
DEFAULT_TIMEOUT = 10
_PREVIEW_PREFERENCE: tuple[str, ...] = (
    "llama-3-8b-instruct:alignment",
    "llama-3-8b-instruct",
)


class TokenPlaceError(RuntimeError):
    """Raised when the token.place API cannot satisfy a request."""


@dataclass(frozen=True)
class ClientIntegration:
    """Mapping between ``token.place`` and a client repository."""

    token_repo: str
    client_repo: str
    detail: str


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
    except requests.RequestException as exc:  # pragma: no cover - network errors mocked
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


def _clean_repo_segment(segment: str) -> str:
    repo = segment.split("/", 1)[0]
    return repo[:-4] if repo.endswith(".git") else repo


def _slug_from_repo_url(url: str) -> str | None:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc and len(parts) >= 2:
        owner, repo = parts[:2]
        return f"{owner}/{_clean_repo_segment(repo)}"
    if parsed.netloc and parts:
        owner = parts[0]
        repo = _clean_repo_segment(parts[-1])
        return f"{owner}/{repo}"

    cleaned = url.strip().strip("/")
    if not cleaned:
        return None
    if cleaned.count("/") >= 1:
        owner, repo = cleaned.split("/", 1)
        return f"{owner}/{_clean_repo_segment(repo)}"
    return cleaned


def quest_detail(
    primary_slug: str,
    secondary_slug: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> str:
    """Return a quest detail string enriched with token.place models."""

    try:
        models = _get_cached_models(base_url=base_url, api_key=api_key)
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


def plan_client_integrations(
    repos: Sequence[str],
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> list[ClientIntegration]:
    """Return integration plans pairing token.place with other repositories."""

    unique: list[str] = []
    seen: set[str] = set()
    for entry in repos:
        slug = _slug_from_repo_url(entry)
        if not slug:
            continue
        key = slug.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(slug)

    token_repos = [slug for slug in unique if "token" in slug.lower()]
    if not token_repos:
        return []

    token_keys = {slug.lower() for slug in token_repos}
    client_repos = [slug for slug in unique if slug.lower() not in token_keys]

    integrations: list[ClientIntegration] = []
    for token_slug in token_repos:
        for client_slug in client_repos:
            detail = quest_detail(
                token_slug,
                client_slug,
                base_url=base_url,
                api_key=api_key,
            )
            integrations.append(
                ClientIntegration(
                    token_repo=token_slug,
                    client_repo=client_slug,
                    detail=detail,
                )
            )
    return integrations


def _normalized_cache_key(
    base_url: str | None, api_key: str | None
) -> tuple[str, str | None]:
    """Return canonical values for ``base_url`` and ``api_key``."""

    resolved_url = _resolve_base_url(base_url)
    resolved_key = _resolve_api_key(api_key)
    return resolved_url, resolved_key


@lru_cache(maxsize=16)
def _cached_models(
    normalized_base_url: str, normalized_api_key: str | None
) -> tuple[str, ...]:
    """Return cached model metadata for token.place."""

    models = list_models(base_url=normalized_base_url, api_key=normalized_api_key)
    return tuple(models)


def _get_cached_models(
    *, base_url: str | None = None, api_key: str | None = None
) -> list[str]:
    """Return token.place models using a simple in-memory cache."""

    normalized_base_url, normalized_api_key = _normalized_cache_key(base_url, api_key)
    return list(_cached_models(normalized_base_url, normalized_api_key))


def _clear_model_cache() -> None:
    """Clear cached token.place model metadata (primarily for tests)."""

    _cached_models.cache_clear()


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for token.place helpers."""

    parser = argparse.ArgumentParser(description="token.place helpers")
    sub = parser.add_subparsers(dest="cmd")

    # Subcommand: list models
    list_cmd = sub.add_parser(
        "list",
        help="List available token.place models",
    )
    list_cmd.add_argument(
        "--base-url",
        default=None,
        help=(
            "token.place API base URL (defaults to AXEL_TOKEN_PLACE_URL or "
            f"{DEFAULT_API_URL})"
        ),
    )
    list_cmd.add_argument(
        "--api-key",
        default=None,
        help=("API key for token.place (defaults to TOKEN_PLACE_API_KEY when unset)"),
    )
    list_cmd.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds (defaults to %(default)s)",
    )

    # Subcommand: plan client integrations
    clients = sub.add_parser(
        "clients",
        help="Plan token.place client integrations across repositories",
    )
    clients.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Repository list (defaults to AXEL_REPO_FILE or repos.txt)",
    )
    clients.add_argument(
        "--base-url",
        default=None,
        help="token.place API base URL",
    )
    clients.add_argument(
        "--api-key",
        default=None,
        help="token.place API key",
    )

    if argv is None:
        parsed_args = sys.argv[1:]
    else:
        parsed_args = list(argv)

    if not parsed_args or parsed_args[0].startswith("-"):
        parsed_args = ["list", *parsed_args]

    args = parser.parse_args(parsed_args)

    if args.cmd == "list":
        try:
            models = list_models(
                base_url=args.base_url, api_key=args.api_key, timeout=args.timeout
            )
        except TokenPlaceError as exc:
            print(f"Failed to list models: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

        if not models:
            print("No models available")
            return

        print("Available models:")
        for model in models:
            print(f"- {model}")
        return

    if args.cmd == "clients":
        path = (
            Path(args.path).expanduser() if args.path is not None else get_repo_file()
        )
        repos = load_repos(path=path)
        integrations = plan_client_integrations(
            repos, base_url=args.base_url, api_key=args.api_key
        )
        if not integrations:
            print("No token.place repositories configured")
            return
        for integration in integrations:
            print(f"- {integration.token_repo} ↔ {integration.client_repo}")
            print(f"  quest: {integration.detail}")
            print()
        return

    parser.print_help()  # pragma: no cover - CLI default output


__all__ = [
    "TokenPlaceError",
    "DEFAULT_API_URL",
    "DEFAULT_TIMEOUT",
    "list_models",
    "quest_detail",
    "ClientIntegration",
    "plan_client_integrations",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
