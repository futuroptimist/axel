"""Helpers for installing shell completion scripts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@dataclass(frozen=True)
class CompletionInstallation:
    """Result describing an installed completion script."""

    shell: str
    path: Path


def _normalize_shell_name(value: str | None, *, strict: bool) -> str:
    """Return a supported shell name from *value*."""

    if not value:
        if strict:
            raise ValueError("shell is required")
        return "bash"

    name = Path(value).name.lower()
    for candidate in _SUPPORTED_SHELLS:
        if name == candidate:
            return candidate
    for candidate in _SUPPORTED_SHELLS:
        if candidate in name:
            return candidate

    if strict:
        raise ValueError(f"unsupported shell: {value}")
    return "bash"


def _detect_shell(env: Mapping[str, str] | None = None) -> str:
    """Infer the active shell from *env*, defaulting to bash."""

    environ = os.environ if env is None else env
    return _normalize_shell_name(environ.get("SHELL"), strict=False)


def _default_destination(shell: str) -> Path:
    """Return the default completion path for *shell*."""

    home = Path.home()
    if shell == "fish":
        return home / ".config" / "fish" / "completions" / "axel.fish"

    suffix = "bash" if shell == "bash" else "zsh"
    return home / ".local" / "share" / "axel" / "completions" / f"axel.{suffix}"


_BASH_TEMPLATE = """# Axel shell completions for bash/zsh
_axel_completions() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    local top_opts='--install-completions --shell --path --help -h'
    local commands='repos tasks analyze-orthogonality analyze-saturation'

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${top_opts}" -- "${cur}") )
        return 0
    fi

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
        return 0
    fi

    local command="${COMP_WORDS[1]}"

    if [[ "${command}" == '--install-completions' ]]; then
        if [[ "${prev}" == '--shell' ]]; then
            COMPREPLY=( $(compgen -W 'bash zsh fish' -- "${cur}") )
        elif [[ ${cur} == -* ]]; then
            COMPREPLY=( $(compgen -W "${top_opts}" -- "${cur}") )
        fi
        return 0
    fi

    case "${command}" in
        repos)
            local repos_opts='add list remove fetch --path --token '\
                '--visibility --help -h'
            COMPREPLY=( $(compgen -W "${repos_opts}" -- "${cur}") )
            ;;
        tasks)
            local tasks_opts='add list complete remove clear --path --help -h'
            COMPREPLY=( $(compgen -W "${tasks_opts}" -- "${cur}") )
            ;;
        analyze-orthogonality)
            local ortho_opts='--diff-file --repo --pr --help -h'
            COMPREPLY=( $(compgen -W "${ortho_opts}" -- "${cur}") )
            ;;
        analyze-saturation)
            local sat_opts='--repo --prompt --metrics --help -h'
            COMPREPLY=( $(compgen -W "${sat_opts}" -- "${cur}") )
            ;;
    esac
}

if [[ -n ${ZSH_VERSION-} ]]; then
    autoload -U +X bashcompinit && bashcompinit
fi

complete -F _axel_completions axel
"""


_FISH_TEMPLATE = """# Axel shell completions for fish
complete -c axel -f
complete -c axel -l install-completions -d 'Install shell completions'
complete -c axel -l shell -r -d 'Shell target' -a 'bash zsh fish' \
    -n '__fish_contains_opt --install-completions'
complete -c axel -l path -r -d 'Output file' \
    -n '__fish_contains_opt --install-completions'
complete -c axel -n '__fish_use_subcommand' -a 'repos' -d 'Manage repository list'
complete -c axel -n '__fish_use_subcommand' -a 'tasks' -d 'Manage tasks'
complete -c axel -n '__fish_use_subcommand' -a 'analyze-orthogonality' \
    -d 'Analyze orthogonality'
complete -c axel -n '__fish_use_subcommand' -a 'analyze-saturation' \
    -d 'Analyze saturation'
complete -c axel -n '__fish_seen_subcommand_from repos' \
    -a 'add list remove fetch'
complete -c axel -n '__fish_seen_subcommand_from tasks' \
    -a 'add list complete remove clear'
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l repo -d 'Repository slug' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l diff-file -d 'Diff file' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l pr -d 'Pull request' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l repo -d 'Repository slug' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l prompt -d 'Prompt name' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l metrics -d 'Metrics file' -r
"""


def _generate_script(shell: str) -> str:
    """Return the completion script for *shell*."""

    if shell == "fish":
        return _FISH_TEMPLATE
    return _BASH_TEMPLATE


def install_completions(
    *, shell: str | None = None, path: str | Path | None = None
) -> CompletionInstallation:
    """Install completion script for *shell* and return the installation info."""

    selected = (
        _normalize_shell_name(shell, strict=True)
        if shell is not None
        else _detect_shell()
    )
    destination = (
        Path(path).expanduser() if path is not None else _default_destination(selected)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_generate_script(selected), encoding="utf-8")
    return CompletionInstallation(shell=selected, path=destination)


__all__ = ["CompletionInstallation", "install_completions"]
