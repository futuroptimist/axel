<!-- BEGIN: AXEL HILLCLIMB -->
# Axel Hillclimb Mode

**What it does:** Given an action card, Axel clones matching repos, creates N branches, and seeds each
with an `AXEL_TASK.md` containing planner/coder/critique prompts and acceptance criteria. The prompts
are documented in [prompts/prompts-hillclimb.md](prompts/prompts-hillclimb.md). By default it’s a dry
run. With `--execute`, it pushes branches and opens **draft** PRs so CI and humans can iterate safely.

## Quickstart
```bash
make install
# Dry run:
make hillclimb
# Execute (opens draft PRs):
make hillclimb-execute
# Specific card:
python .axel/hillclimb/scripts/axel.py hillclimb --card add-pipx-install --execute
# Update dashboard:
python .axel/hillclimb/scripts/axel.py dashboard
Configure
.axel/hillclimb/repos.yml: which repos to target.

.axel/hillclimb/config.yml: runs, touch budgets, labels, selection mode.

.axel/hillclimb/cards/*.yml: action cards (acceptance criteria + constraints).
See [example action cards](prompts/prompts-hillclimb.md#example-action-cards).

.env: set GITHUB_TOKEN= (see .env.example).

Notes

Safe by default (dry-run). No changes go upstream until --execute.

Branch names: hc/<owner_repo>/<card>/<timestamp>-rN.

PRs are draft with labels from config.

<!-- END: AXEL HILLCLIMB -->
