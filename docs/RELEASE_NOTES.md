# Release Notes

## v0.1.0 (Unreleased)

### What's New
- Ship `infra/docker-compose-mock.yml` so the token.place server, relay, and mock
  model boot with a single `docker compose` command.
- Keep `repos.txt` deterministic by ensuring `load_repos` sorts URLs
  case-insensitively whenever entries are added or fetched from GitHub.
- Document the hillclimb workflow, Discord ingestion, and security posture so new
  contributors can trace how automation fits together before the first run.

### Try it in 60s
- `pipx install axel` then run `axel repos list` to confirm the CLI wiring.
- Clone this repository and run `docker compose -f infra/docker-compose-mock.yml up`
  to explore the local token.place stack without additional configuration.
- Point `AXEL_REPO_FILE` or `--path` at a custom repo list to see deterministic
  quest suggestions across your projects.

### Roadmap next
- Record a 90-second demo video that walks through the Quickstart and highlights
  cross-repo quests backed by token.place metadata.
- Cut the v0.1.0 tag once the demo and supporting docs are ready, then publish the
  release on GitHub with these notes.
- Continue onboarding additional repos from the flywheel so analytics span the
  broader project set.

Automated coverage: `tests/test_release_readiness_dashboard.py::test_release_notes_cover_v0_sections`
keeps these sections present and populated.
