<!-- BEGIN: AXEL HILLCLIMB -->
# Axel Hillclimb Mode

**What it does:** Given an action card, Axel clones matching repos, creates N branches, and seeds each
with an `AXEL_TASK.md` containing planner/coder/critique prompts and acceptance criteria. The prompts
are documented in [prompts/codex/prompts-hillclimb.md](prompts/codex/prompts-hillclimb.md). By default it’s a dry
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
```

Configure
.axel/hillclimb/repos.yml: which repos to target.

.axel/hillclimb/config.yml: runs, touch budgets, labels, selection mode.

.axel/hillclimb/cards/*.yml: action cards (acceptance criteria + constraints).
See [example action cards](prompts/codex/prompts-hillclimb.md#example-action-cards).

.env: set GITHUB_TOKEN= (see .env.example).

Notes

Safe by default (dry-run). No changes go upstream until --execute.

Branch names: hc/<owner_repo>/<card>/<timestamp>-rN.

PRs are draft with labels from config.

<!-- END: AXEL HILLCLIMB -->

## Working-hours guard

Hillclimb blocks repository mutations **Monday–Friday, 09:00 inclusive to 17:00
exclusive in `America/Los_Angeles`** by default. The IANA time zone follows
Pacific daylight saving time; this is not a fixed UTC offset. Weekends are
unblocked by this policy. Being outside the window does not grant permission to
perform any operation.

Customize the `working_hours` section in `.axel/hillclimb/config.yml` for your own
fork or clone. The defaults are generic; no personal context is needed:

```yaml
working_hours:
  enabled: true
  timezone: "America/Los_Angeles"
  weekdays: [monday, tuesday, wednesday, thursday, friday]
  start: "09:00"
  end: "17:00"
```

Use an IANA zone such as `Europe/London` or `UTC`, lowercase weekday names, and
quoted 24-hour `HH:MM` times. The window must start and end on the same day, with
start before end. Omitted fields use the defaults above. An explicit
`enabled: false` disables this policy for a deployment that does not need it.
Missing files, invalid zones, invalid schedules, and unknown setting names stop
the runner instead of silently allowing mutations.

The guard applies to both `hillclimb --execute` and `hillclimb --dry-run`: the
existing dry run still clones repositories, creates local branches and commits,
and removes its local branches; only pushing and opening PRs are skipped. The
runner checks before starting and again before each Git mutation, task-file
write, GitHub POST (including PR creation and labels), and dashboard write. If a
run crosses into working hours, it stops before the next mutation and leaves
any already-created local files or branches in place for inspection. It does not
roll back, queue work, or resume automatically. Review that state before retrying
outside the blocked window. Commands already in progress are not interrupted.

Read-only inspection and planning may continue, including `version` and staged
diff inspection. This is a guard for the hillclimb runner, not a system-wide Git
hook or a restriction on unrelated Axel commands or external tools. Other
agents/scripts can call the same read-only check immediately before a mutation:

```bash
python -m axel.working_hours --config .axel/hillclimb/config.yml && git commit
```

The check exits `0` when the schedule allows mutations, `1` during blocked hours,
and `2` for invalid configuration. With no `--config`, it uses the built-in
defaults. Recheck at every later mutation rather than treating an earlier check
as lasting permission. The `tzdata` dependency provides IANA time-zone data on
systems that do not ship it.
