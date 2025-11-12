# Axel — Local Agent Prompt (Web UI Edition): **OpenHands + LM Studio**

This is the web‑first path for running Axel’s local agent with a **browser UI** (no IDE dependency). It uses:

- **OpenHands** for the agent workspace (chat + terminal + browser + change review).
- **LM Studio** to serve a **local, OpenAI‑compatible** LLM endpoint.
- A **repo‑local microagent** so Axel’s guidance is always loaded in context.

This replaces the older “VS Code + extension / Cursor” emphasis. Those editor options are still listed near the end, but the **primary** workflow is a self‑hosted web app.

---

## TL;DR (4090‑ready)

1. Install **LM Studio**, download **Devstral Small 2505**, set context ≥ **32k**, start the **OpenAI‑compatible** server on port `1234`.  
2. Start **OpenHands** and open `http://localhost:3000`.  
3. In OpenHands → **Settings → LLM**, set `Base URL = http://host.docker.internal:1234/v1`, `Custom Model = openai/mistralai/devstral-small-2505`, `API Key = local-llm`.  
4. In your repo, add an **Axel microagent** at `.openhands/microagents/axel.md` (paste Axel’s rules there).  
5. (Optional) Add `.openhands/setup.sh` and `.openhands/pre-commit.sh` to install deps and gate commits/tests.

**Why Devstral Small 2505?** OpenHands’ official “Local LLMs” guide recommends **LM Studio + Devstral Small 2505** (≥16 GB VRAM) and shows the exact GUI settings and base URL; a 4090 (24 GB) is comfortably within spec. :contentReference[oaicite:0]{index=0}

---

## What you get

- **Web UI**: chat panel + **Changes** tab, **Terminal** tab, **Browser** tab. Easy to review diffs and terminal output as the agent works. :contentReference[oaicite:1]{index=1}
- **Git provider integration** (GitHub/GitLab/Bitbucket) managed in Settings. :contentReference[oaicite:2]{index=2}
- **Repo‑level customization** via `.openhands/` (microagents, setup scripts, pre‑commit). :contentReference[oaicite:3]{index=3}
- **Local LLM** using LM Studio’s **OpenAI‑compatible** server (`/v1/chat/completions`, `/v1/responses`, etc.). :contentReference[oaicite:4]{index=4}

---

## Install & Run

### 1) LM Studio (local model server)

**Install LM Studio** and open it.

**Download the model**:
- Use the “Discover” tab. Search for **Devstral Small 2505** (Mistral AI). Download it.  
- Set **Context Length ≥ 32768**; enable **Flash Attention**; then **Load Model**.  
- Turn on the local **OpenAI‑compatible server** and note the **Model API Identifier** (e.g., `mistralai/Devstral-Small-2505`). :contentReference[oaicite:5]{index=5}

**LM Studio server endpoint** (defaults):
- Base URL will look like `http://localhost:1234/v1` (OpenAI‑compatible).  
- LM Studio documents the OpenAI‑compat endpoints and tool/function calling support. :contentReference[oaicite:6]{index=6}

> Tip: For heavy agent runs, keep the model pinned and avoid auto‑eviction while OpenHands is active.

### 2) OpenHands (web UI)

You can run OpenHands via Docker or via the CLI. The GUI serves at **`http://localhost:3000`**.

**Docker (recommended)**

```bash
docker pull docker.openhands.dev/openhands/runtime:0.62-nikolaik

docker run -it --rm --pull=always \
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.openhands.dev/openhands/runtime:0.62-nikolaik \
  -e LOG_ALL_EVENTS=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.openhands:/.openhands \
  -p 3000:3000 \
  --add-host host.docker.internal:host-gateway \
  --name openhands-app \
  docker.openhands.dev/openhands/openhands:0.62
```

Then open **`http://localhost:3000`**. :contentReference[oaicite:7]{index=7}

> **Networking note:** `host.docker.internal` allows the containerized OpenHands app to reach the LM Studio server running on your host at `http://host.docker.internal:1234/v1`. :contentReference[oaicite:8]{index=8}

---

## Wire OpenHands to LM Studio

In the OpenHands UI:

1. Go to **Settings → LLM** and click **see advanced settings**.  
2. Set:
   - **Custom Model**: `openai/mistralai/devstral-small-2505`  
     *(prefix the LM Studio model ID with `openai/` as per the guide).*  
   - **Base URL**: `http://host.docker.internal:1234/v1`  
   - **API Key**: `local-llm` *(any placeholder is fine)*  
3. Save. Start a new conversation. :contentReference[oaicite:9]{index=9}

---

## Add Axel as a repo‑local microagent

OpenHands loads **microagents** from your repository. Use them to inject Axel’s local prompt/rules and keep them versioned with your code. :contentReference[oaicite:10]{index=10}

**Create:** `.openhands/microagents/axel.md`

```markdown
---
name: Axel
type: repo
triggers:
  - "axel"
  - "local agent"
visibility: private
---

# Axel – Local Agent Guidelines

Describe Axel’s house rules here. Keep it concise and actionable:
- Repository conventions (branch naming, commit style).
- Test + lint commands.
- Framework/toolchain versions.
- “Don’t break” constraints & safety rails.
- Review checklist Axel must follow before pushing commits/PRs.

(You can paste or adapt the prior LOCAL_AGENT_PROMPT content here.)
```

> **Always‑on guidance:** Microagents of `type: repo` are included in context for new conversations within this repo. :contentReference[oaicite:11]{index=11}

---

## Optional: repo setup & commit gates

**Bootstrap on start:** `.openhands/setup.sh` runs at session start. Good for installing dev deps and seeding test data. :contentReference[oaicite:12]{index=12}

```bash
#!/usr/bin/env bash
set -euo pipefail

# Python
uv pip install -U -r requirements.txt

# Node
if [ -f package-lock.json ] || [ -f pnpm-lock.yaml ] || [ -f bun.lockb ]; then
  (command -v pnpm >/dev/null && pnpm i) || (command -v bun >/dev/null && bun i) || npm ci
fi

# Repo-wide environment
export NODE_OPTIONS=--max-old-space-size=4096
```

**Pre‑commit gate:** `.openhands/pre-commit.sh` installs as a git hook; instruct the agent to run it before committing. :contentReference[oaicite:13]{index=13}

```bash
#!/usr/bin/env bash
set -euo pipefail

# Fast checks
ruff check . || true
black --check . || true
npm run -s lint || true
npm -s test -- --watch=false || true

# Block on critical failures if you want:
# exit 1
```

> Note: Current behavior may require explicitly telling the agent to run the pre‑commit script before making a commit/PR. :contentReference[oaicite:14]{index=14}

---

## Recommended local model (BiS) for a 4090

- **Primary (BiS)**: **Devstral Small 2505** via LM Studio. This is the model the OpenHands team recommends for local agent workflows, with documented LM Studio settings and context‑length guidance. It’s tuned on real GitHub issues for agent‑style coding tasks and runs well on ≥16 GB VRAM (4090 has 24 GB). :contentReference[oaicite:15]{index=15}

**Alternatives** (also available in LM Studio’s catalog):
- **Qwen2.5‑Coder (14B/32B) Instruct** – strong open‑source code models with published results across code benchmarks; you can try 14B for speed and 32B for quality (with aggressive quantization). :contentReference[oaicite:16]{index=16}
- **DeepSeek‑Coder‑V2‑Lite (16B MoE)** – good code performance at modest active parameters; useful when you want a “bigger brain” feel with acceptable latency locally. :contentReference[oaicite:17]{index=17}

> Practical tip: Whatever you run, set the model’s **context length ≥ 32k**; OpenHands’ system prompt and task history are large, and small contexts can break agent behavior. :contentReference[oaicite:18]{index=18}

---

## Using the web UI

- Start a conversation, describe the task, and let the agent plan.  
- Watch the **Changes** tab to inspect diffs before committing.  
- Use the **Terminal** tab for logs or quick checks; the agent can run commands.  
- The **Browser** tab lets it research docs as needed. :contentReference[oaicite:19]{index=19}

**Connect Git providers** under **Settings → Integrations** to allow the agent to branch/commit/open PRs. :contentReference[oaicite:20]{index=20}

---

## Troubleshooting

- **OpenHands can’t reach LM Studio**  
  Ensure your OpenHands container uses `--add-host host.docker.internal:host-gateway`, and set **Base URL** to `http://host.docker.internal:1234/v1`. Verify LM Studio’s server is on port `1234`. :contentReference[oaicite:21]{index=21}

- **Context too small / agent loops**  
  Increase model **Context Length** to 32k+ in LM Studio; reload the model. :contentReference[oaicite:22]{index=22}

- **PRs skip your pre‑commit**  
  Ask the agent to run `.openhands/pre-commit.sh` before committing, or add a microagent note that enforces this step. :contentReference[oaicite:23]{index=23}

- **Single‑user expectation**  
  The OSS GUI is designed for **single‑user local** runs (no built‑in multi‑tenant auth). If you expose it remotely, put it behind auth/VPN. :contentReference[oaicite:24]{index=24}

---

## Why web‑first?

This flow gives you a **self‑hosted, IDE‑agnostic** agent workspace. It’s also resilient when editor agents are rate‑limited or temporarily down (e.g., recent Copilot Agent action failures discussed in the GitHub community). :contentReference[oaicite:25]{index=25}

---

## Optional: Editor‑based alternatives

- **VS Code + Cline** (open‑source): an in‑editor coding agent with planning, terminal usage, file edits, and MCP integration. Good when you prefer to stay in VS Code. :contentReference[oaicite:26]{index=26}  
- **Cursor** (proprietary): popular editor with agentic features; keep it as a secondary option to this web UI workflow.

---

## Appendix: Full commands & references

**LM Studio: OpenAI‑compatible endpoint** (examples and base URL setting)  
See LM Studio’s “OpenAI Compatibility Endpoints.” :contentReference[oaicite:27]{index=27}

**OpenHands + LM Studio quickstart** (model choice, context settings, base URL, Docker run)  
OpenHands “Local LLMs” guide (LM Studio + Devstral Small 2505). :contentReference[oaicite:28]{index=28}

**OpenHands GUI features** (chat/changes/terminal/browser)  
OpenHands “Key Features.” :contentReference[oaicite:29]{index=29}

**Repo customization & microagents**  
OpenHands “Repository Customization” and “Microagents Overview.” :contentReference[oaicite:30]{index=30}

---
