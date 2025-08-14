#!/usr/bin/env python3
import argparse
import hashlib
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]  # repo root
AXEL_DIR = ROOT / ".axel" / "hillclimb"
WORK_DIR = AXEL_DIR / "work"
PROMPTS_DIR = AXEL_DIR / "prompts"
CARDS_DIR = AXEL_DIR / "cards"
CONFIG = AXEL_DIR / "config.yml"
REPOS = AXEL_DIR / "repos.yml"


def sh(cmd, cwd=None, check=True):
    p = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({cwd}): {cmd}\n{p.stdout}")
    return p.stdout.strip()


def load_yaml(p):
    return yaml.safe_load(Path(p).read_text()) if Path(p).exists() else {}


def gh_headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def gh_get(token, url):
    r = requests.get(url, headers=gh_headers(token), timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"GitHub GET {url} -> {r.status_code}: {r.text}")
    return r.json()


def gh_post(token, url, payload):
    r = requests.post(url, headers=gh_headers(token), json=payload, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"GitHub POST {url} -> {r.status_code}: {r.text}")
    return r.json()


def ensure_clone(slug, default_branch):
    owner, repo = slug.split("/")
    target = WORK_DIR / f"{owner}__{repo}"
    if not target.exists():
        sh(f"git clone https://github.com/{slug}.git {target}")
    else:
        sh("git fetch --all --prune", cwd=target)
    # Ensure we’re on the default branch and up to date
    sh(f"git checkout {default_branch}", cwd=target)
    sh(f"git pull --ff-only origin {default_branch}", cwd=target)
    return target


def make_branch_name(prefix, repo, card_key, attempt):
    ts = time.strftime("%Y%m%d-%H%M%S")
    safe = repo.replace("/", "_")
    return f"{prefix}/{safe}/{card_key}/{ts}-r{attempt}"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read(p):
    return Path(p).read_text(encoding="utf-8")


def fingerprint_patch(repo_dir):
    try:
        diff = sh("git diff --staged", cwd=repo_dir)
    except RuntimeError:
        return ""
    return hashlib.sha1(diff.encode("utf-8")).hexdigest()


def create_task_markdown(slug, card, attempt, cfg, prompts):
    tb = card.get("constraints", {})
    files_max = tb.get("files_max", cfg["touch_budget"]["files_max"])
    loc_max = tb.get("loc_max", cfg["touch_budget"]["loc_max"])
    plan_p = read(PROMPTS_DIR / "plan.md")
    code_p = read(PROMPTS_DIR / "code.md")
    crit_p = read(PROMPTS_DIR / "critique.md")

    ac_lines = "\n".join([f"- {x}" for x in card.get("acceptance_criteria", [])])
    must_pass = "\n".join([f"- {x}" for x in card.get("must_pass", [])]) or "- (none)"
    nice = "\n".join([f"- {x}" for x in card.get("nice_to_have", [])]) or "- (none)"

    body = f"""# AXEL TASK: {card['title']} (Run {attempt})

**Repo:** `{slug}`
**Card:** `{card['key']}`
**Touch budget:** ≤ {files_max} files, ≤ {loc_max} LOC

## Acceptance criteria
{ac_lines}

## CI must pass
{must_pass}

## Nice to have
{nice}

---

## Planner Prompt
{plan_p}

shell
Copy

## Coder Prompt
{code_p}

shell
Copy

## Self-Critique Prompt
{crit_p}

bash
Copy

    > Implement the smallest viable change that satisfies the acceptance
    > criteria within the touch budget. Include tests and docs updates.
    > Do not add secrets. Prefer conventional commits in separate commits if
    > needed.
"""
    return body


def open_draft_pr(
    token, slug, head_branch, base_branch, title, body, labels, draft=True
):
    url = f"https://api.github.com/repos/{slug}/pulls"
    payload = {
        "title": title,
        "head": head_branch,
        "base": base_branch,
        "body": body,
        "draft": draft,
    }
    pr = gh_post(token, url, payload)
    # Add labels (best-effort)
    try:
        issues_url = f"https://api.github.com/repos/{slug}/issues/{pr['number']}/labels"
        gh_post(token, issues_url, {"labels": labels})
    except Exception as e:
        print(f"Labeling failed: {e}")
    return pr


def cmd_hillclimb(args):
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token and args.execute:
        raise SystemExit(
            "GITHUB_TOKEN/GH_TOKEN not set. Use .env or environment variables."
        )
    cfg = load_yaml(CONFIG)
    repos = load_yaml(REPOS).get("repos", [])
    cards = []
    for p in CARDS_DIR.glob("*.yml"):
        card = load_yaml(p)
        if card:
            cards.append(card)

    # Choose card (simple: first enabled repo match; optional --card)
    selected_cards = [c for c in cards if (args.card is None or c["key"] == args.card)]
    if not selected_cards:
        raise SystemExit("No matching action cards found.")
    card = selected_cards[0]

    # Determine applicable repos
    applies = set(card.get("applies_to", []))
    targets = []
    for r in repos:
        if not r.get("enabled", True):
            continue
        repo_name = r["slug"].split("/")[1].lower()
        if not applies or any(a.lower() in repo_name for a in applies):
            targets.append(r)

    if not targets:
        print("No target repos matched; exiting.")
        return

    print(f"Selected card: {card['key']}  → targets: {[t['slug'] for t in targets]}")
    for r in targets:
        slug = r["slug"]
        default_branch = r.get("default_branch", "main")
        try:
            repo_dir = ensure_clone(slug, default_branch)
        except RuntimeError as e:
            print(f"Skipping {slug}: {e}")
            continue

        for attempt in range(1, args.runs + 1):
            branch = make_branch_name(cfg["branch_prefix"], slug, card["key"], attempt)
            print(f"Preparing attempt {attempt} for {slug}: {branch}")

            # Create branch
            sh(f"git checkout -b {branch}", cwd=repo_dir)

            # Write task file
            task_path = Path(repo_dir) / "AXEL_TASK.md"
            task_body = create_task_markdown(slug, card, attempt, cfg, PROMPTS_DIR)
            write(task_path, task_body)
            sh(f'git add "{task_path.name}"', cwd=repo_dir)
            commit_msg = (
                f"chore(axel): seed hillclimb attempt for {card['key']} [run {attempt}]"
            )
            sh(f'git commit -m "{commit_msg}"', cwd=repo_dir)

            if args.execute:
                sh(f"git push -u origin {branch}", cwd=repo_dir)
                title = f"feat(hillclimb): {card['title']} [run #{attempt}]"
                pr = open_draft_pr(
                    token,
                    slug,
                    head_branch=branch,
                    base_branch=default_branch,
                    title=title,
                    body=task_body,
                    labels=cfg.get("labels", []),
                    draft=cfg.get("pr", {}).get("draft", True),
                )
                print(f"Opened draft PR: {pr.get('html_url')}")
            else:
                print(f"[DRY RUN] Would push branch and open PR for {slug}:{branch}")

            # Return to default branch and delete local branch if dry-run
            sh(f"git checkout {default_branch}", cwd=repo_dir)
            if not args.execute:
                sh(f"git branch -D {branch}", cwd=repo_dir)

    print("Hillclimb operation complete.")


def cmd_dashboard(_args):
    # Generate or update a simple release-readiness dashboard doc with markers
    doc = ROOT / "docs" / "RELEASE-READINESS-DASHBOARD.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    content = doc.read_text() if doc.exists() else ""
    start = "<!-- BEGIN: AXEL HILLCLIMB -->"
    end = "<!-- END: AXEL HILLCLIMB -->"
    header = (
        "| Repo | v0.1 tag | Release notes | 1‑click install | Demo | "
        "Landing page | CI green | "
        "Coverage badge | Security scans | Arch doc |"
    )
    table = textwrap.dedent(
        f"""
    # Release‑Readiness Dashboard (Axel)

    > Legend: `[ ]` = not started · `[x]` = done

    {header}
    |---|---|---|---|---|---|---|---|---|---|
    | token.place | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | f2clipboard | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | flywheel | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | gitshelves | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | sugarkube | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | sigma | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    | dspace | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
    """
    ).strip()

    block = f"{start}\n{table}\n{end}\n"
    if start in content and end in content:
        pre = content.split(start)[0]
        post = content.split(end)[1]
        new = f"{pre}{block}{post}"
    else:
        new = block if not content else f"{content}\n\n{block}"
    doc.write_text(new, encoding="utf-8")
    print(f"Updated dashboard at {doc.relative_to(ROOT)}")


def cmd_version(_args):
    print("axel hillclimb CLI v0.1.0")


def main():
    parser = argparse.ArgumentParser(prog="axel")
    sub = parser.add_subparsers()

    p_hc = sub.add_parser("hillclimb", help="Create N draft PR attempts across repos")
    p_hc.add_argument("--runs", type=int, default=4)
    p_hc.add_argument(
        "--card", type=str, default=None, help="Card key (default: first match)"
    )
    p_hc.add_argument(
        "--execute", action="store_true", help="Push branches and open draft PRs"
    )
    p_hc.add_argument(
        "--dry-run", dest="execute", action="store_false", help="Dry run (default)"
    )
    p_hc.set_defaults(func=cmd_hillclimb)

    p_dash = sub.add_parser(
        "dashboard", help="Update the release-readiness dashboard doc"
    )
    p_dash.set_defaults(func=cmd_dashboard)

    p_ver = sub.add_parser("version", help="Print CLI version")
    p_ver.set_defaults(func=cmd_version)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(2)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
