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
    local commands='repos tasks analyze-orthogonality analyze-saturation config'

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
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local repos_sub='add list remove fetch'
                COMPREPLY=( $(compgen -W "${repos_sub}" -- "${cur}") )
            else
                local repos_subcommand="${COMP_WORDS[2]}"
                case "${repos_subcommand}" in
                    list)
                        local repos_list_opts='--sample --seed --path --json --help -h'
                        COMPREPLY=( $(compgen -W "${repos_list_opts}" -- "${cur}") )
                        ;;
                    fetch)
                        local repos_fetch_opts='--token --visibility --path --json '\
                            '--help -h'
                        COMPREPLY=( $(compgen -W "${repos_fetch_opts}" -- "${cur}") )
                        ;;
                    add|remove)
                        local repos_modify_opts='--path --json --help -h'
                        COMPREPLY=( $(compgen -W "${repos_modify_opts}" -- "${cur}") )
                        ;;
                    *)
                        local repos_common_opts='--path --json --help -h'
                        COMPREPLY=( $(compgen -W "${repos_common_opts}" -- "${cur}") )
                        ;;
                esac
            fi
            ;;
        tasks)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local tasks_sub='add list complete remove clear'
                COMPREPLY=( $(compgen -W "${tasks_sub}" -- "${cur}") )
            else
                local tasks_subcommand="${COMP_WORDS[2]}"
                if [[ "${tasks_subcommand}" == 'list' ]]; then
                    local tasks_list_opts='--sample --seed --path --json --help -h'
                    COMPREPLY=( $(compgen -W "${tasks_list_opts}" -- "${cur}") )
                else
                    local tasks_common_opts='--path --json --help -h'
                    COMPREPLY=( $(compgen -W "${tasks_common_opts}" -- "${cur}") )
                fi
            fi
            ;;
        analyze-orthogonality)
            local ortho_opts='--diff-file --repo --pr --json --sample --seed --help -h'
            COMPREPLY=( $(compgen -W "${ortho_opts}" -- "${cur}") )
            ;;
        analyze-saturation)
            local sat_opts='--repo --prompt --metrics --json --help -h'
            COMPREPLY=( $(compgen -W "${sat_opts}" -- "${cur}") )
            ;;
        config)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                local cfg_opts='telemetry --help -h'
                COMPREPLY=( $(compgen -W "${cfg_opts}" -- "${cur}") )
            else
                local cfg_subcommand="${COMP_WORDS[2]}"
                if [[ "${cfg_subcommand}" == 'telemetry' ]]; then
                    local tele_opts='--enable --disable --status --yes --help -h'
                    COMPREPLY=( $(compgen -W "${tele_opts}" -- "${cur}") )
                fi
            fi
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
complete -c axel -n '__fish_use_subcommand' -a 'config' -d 'Manage configuration'
complete -c axel -n '__fish_seen_subcommand_from repos' \
    -a 'add list remove fetch'
complete -c axel -n '__fish_seen_subcommand_from repos' \
    -l json -d 'Output JSON'
complete -c axel -n '__fish_seen_subcommand_from repos list' \
    -l sample -d 'Return a deterministic subset of repositories' -r
complete -c axel -n '__fish_seen_subcommand_from repos list' \
    -l seed -d 'Seed used when sampling repositories' -r
complete -c axel -n '__fish_seen_subcommand_from tasks' \
    -a 'add list complete remove clear'
complete -c axel -n '__fish_seen_subcommand_from tasks' \
    -l json -d 'Output JSON'
complete -c axel -n '__fish_seen_subcommand_from tasks list' \
    -l sample -d 'Return a deterministic subset of tasks' -r
complete -c axel -n '__fish_seen_subcommand_from tasks list' \
    -l seed -d 'Seed used when sampling tasks' -r
complete -c axel -n '__fish_seen_subcommand_from config' \
    -a 'telemetry' -d 'Manage telemetry opt-in'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -l enable -d 'Enable telemetry'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -l disable -d 'Disable telemetry'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -l status -d 'Show telemetry status'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -l yes -d 'Auto-confirm prompts'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -l help -d 'Show help'
complete -c axel -n '__fish_seen_subcommand_from config telemetry' \
    -s h -d 'Show help'
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l repo -d 'Repository slug' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l diff-file -d 'Diff file' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l pr -d 'Pull request' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l json -d 'Output orthogonality analytics as JSON'
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l sample -d 'Analyze a deterministic subset of diff files' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-orthogonality' \
    -l seed -d 'Seed used when sampling diff files' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l repo -d 'Repository slug' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l prompt -d 'Prompt name' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l metrics -d 'Metrics file' -r
complete -c axel -n '__fish_seen_subcommand_from analyze-saturation' \
    -l json -d 'Output saturation analytics as JSON'
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
