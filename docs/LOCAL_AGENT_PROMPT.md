# Axel — Local Agent Prompt (Web UI Edition): **OpenHands + LM Studio**

This is the web-first path for running Axel’s local agent with a **browser UI** (no IDE dependency). It uses:

- **OpenHands** for the agent workspace (chat + terminal + browser + change review).
- **LM Studio** to serve a **local, OpenAI-compatible** LLM endpoint.
- A **repo-local microagent** so Axel’s guidance is always loaded in context.

This replaces the older “VS Code + extension / Cursor” emphasis. Those editor options are still listed near the end, but the **primary** workflow is a self-hosted web app.

---

## TL;DR (4090-ready)

1. Install **LM Studio**, download **Devstral Small 2505**, set context ≥ **32k**, start the **OpenAI-compatible** server on port `1234`.  
2. Start **OpenHands** and open `http://localhost:3000` (or remap to another host port; see below).  
3. In OpenHands → **Settings → LLM**, set  
   `Base URL = http://host.docker.internal:1234/v1`,  
   `Custom Model = openai/mistralai/devstral-small-2505`,  
   `API Key = local-llm`.  
4. In your repo, add an **Axel microagent** at `.openhands/microagents/axel.md` (paste Axel’s rules there).  
5. (Optional) Add `.openhands/setup.sh` and `.openhands/pre-commit.sh` to install deps and gate commits/tests.

**Why Devstral Small 2505?** OpenHands’ **Local LLMs** guide recommends **LM Studio + Devstral Small 2505** for agent-style coding and shows the exact GUI/base-URL wiring. A 4090 (24 GB) is comfortably within spec.  
References: [OpenHands: Local LLMs (LM Studio + Devstral)](https://docs.openhands.dev/openhands/usage/llms/local-llms), [LM Studio OpenAI-compatible server (port 1234)](https://lmstudio.ai/docs/developer/openai-compat), [Devstral model card (131,072-token context)](https://huggingface.co/lmstudio-community/Devstral-Small-2505-GGUF)

---

## What you get

- **Web UI**: chat panel + **Changes** tab, **Terminal** tab, **Browser** tab.  
- **Git provider integration** (GitHub/GitLab/Bitbucket) in Settings.  
- **Repo-level customization** via `.openhands/` (microagents, setup scripts, pre-commit).  
- **Local LLM** through LM Studio’s OpenAI-compatible server (`/v1/*`).

References: [OpenHands: Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)

---

## Install & Run

### 1) LM Studio (local model server)

**Install LM Studio** and open it.

**Download the model**:
- Discover **Devstral Small 2505** (Mistral AI) and download it.
- Load with these **baseline settings for a 4090**:
  - **Context Length:** **32,768** tokens (set ≥32k; Devstral supports up to **131,072**).  
  - **Flash Attention:** **On**  
  - **GPU Offload:** **Max** (all layers for your quant)  
  - **Offload KV Cache to GPU:** **On** (disable only if you push very large contexts and hit VRAM ceilings)  
  - **Keep Model in Memory:** **On**  
  - **Try mmap():** **On**  
  - **Evaluation Batch Size:** leave default unless you see throttling  
  - **RoPE Base/Scale:** **Auto**

**Start the local server** (OpenAI-compatible): use LM Studio’s UI (Developer → **Start Server**) or CLI; the default base URL is:

```
http://localhost:1234/v1
```

References: [LM Studio OpenAI-compat endpoints](https://lmstudio.ai/docs/developer/openai-compat), [LM Studio developer docs](https://lmstudio.ai/docs/developer), [Devstral context length](https://huggingface.co/lmstudio-community/Devstral-Small-2505-GGUF)

> Tip: For long agent runs, keep the model pinned and avoid auto-eviction while OpenHands is active.

### 2) OpenHands (web UI)

You can run OpenHands via Docker or via the CLI. The GUI serves inside the container on **port 3000**.

**Happy-path (port 3000 is free):**

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

Then open:

```
http://localhost:3000
```

**Change the host port (if 3000 is busy)**

- **Bash / Linux / WSL:**

```bash
docker run -it --rm \
  -p 3333:3000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$HOME/.openhands":"/.openhands" \
  --name openhands \
  docker.openhands.dev/openhands/openhands:latest
```

- **PowerShell (Windows):**

```powershell
docker run -it --rm `
  -p 3333:3000 `
  -v "//var/run/docker.sock:/var/run/docker.sock" `
  -v "${env:USERPROFILE}\.openhands:/.openhands" `
  --name openhands `
  docker.openhands.dev/openhands/openhands:latest
```

Now open:

```
http://localhost:3333
```

> **Networking note:** On Docker Desktop, `host.docker.internal` lets the container reach services on your host (LM Studio at `http://host.docker.internal:1234/v1`).  
References: [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/), [How-tos](https://docs.docker.com/desktop/features/networking/networking-how-tos/)

---

## Wire OpenHands to LM Studio

In the OpenHands UI:

1. Go to **Settings → LLM** and click **see advanced settings**.  
2. Set:
   - **Custom Model**: `openai/mistralai/devstral-small-2505`  
     *(prefix the LM Studio model ID with `openai/` as shown in the guide).*  
   - **Base URL**: `http://host.docker.internal:1234/v1`  
   - **API Key**: `local-llm` *(any placeholder is fine)*  
3. **Save**, then start a new conversation.

Reference: [OpenHands: Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)

---

## Add Axel as a repo-local microagent

OpenHands loads **microagents** from your repository. Use them to inject Axel’s local prompt/rules and keep them versioned with your code.

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

> **Always-on guidance:** Microagents of `type: repo` are included in context for new conversations within this repo.  
Reference: [OpenHands: Microagents & repo customization](https://docs.openhands.dev/openhands/usage/repository-customization)

---

## Optional: repo setup & commit gates

**Bootstrap on start:** `.openhands/setup.sh` runs at session start. Good for installing dev deps and seeding test data.

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

**Pre-commit gate:** `.openhands/pre-commit.sh` installs as a git hook; instruct the agent to run it before committing.

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

> Note: Depending on version, you may need to explicitly tell the agent to run the pre-commit script before committing/PRs.  
Reference: [OpenHands: Repository customization](https://docs.openhands.dev/openhands/usage/repository-customization)

---

## Recommended local model (BiS) for a 4090

- **Primary (BiS)**: **Devstral Small 2505** via LM Studio (OpenHands’ recommended pairing for local agent workflows). Devstral supports **131,072** tokens if you need huge windows; for speed, **32k** is a great default for agent runs.

**Alternatives** (also available in LM Studio’s catalog):
- **Qwen2.5-Coder (14B/32B) Instruct** — strong open-source code models; 14B is fast, 32B for quality (quantize as needed).
- **DeepSeek-Coder-V2-Lite (MoE)** — competitive code performance with modest active parameters.

References: [OpenHands: Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms), [Devstral context length](https://huggingface.co/lmstudio-community/Devstral-Small-2505-GGUF)

> Practical tip: Keep **Context Length ≥ 32k**; small windows can break agent behavior (lost plan/history). Bump to 65k/128k for giant diffs or long browsing traces—accepting slower throughput.

---

## Using the web UI

- Start a conversation, describe the task, and let the agent plan.  
- Watch the **Changes** tab to inspect diffs before committing.  
- Use the **Terminal** tab for logs or quick checks; the agent can run commands.  
- The **Browser** tab lets it research docs as needed.

References: [OpenHands: Local LLMs](https://docs.openhands.dev/openhands/usage/llms/local-llms)

---

## Troubleshooting

- **OpenHands can’t reach LM Studio**  
  Use `host.docker.internal` in the Base URL and ensure LM Studio’s server is on port `1234`. On Linux servers (no Docker Desktop), replace with the host IP or a user-defined bridge network.  
  References: [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/)

- **Change UI port (host)**  
  Remap with `-p NEW_PORT:3000` (examples above). If you find a version where the UI ignores mapping, upgrade to a current image; older issues around port changes have been fixed.  
  Reference: [historical discussion](https://github.com/All-Hands-AI/OpenHands/issues/3288)

- **Context too small / agent loops**  
  Increase model **Context Length** to **32k+** in LM Studio; reload the model.

- **PRs skip your pre-commit**  
  Ask the agent to run `.openhands/pre-commit.sh` before committing, or enforce in your microagent instructions.

- **Single-user expectation**  
  The OSS GUI targets **single-user local** runs (no built-in multi-tenant auth). If you expose it, put it behind auth/VPN.

---

## Why web-first?

This flow gives you a **self-hosted, IDE-agnostic** agent workspace—and it keeps working when editor agents are rate-limited or temporarily down.

---

## Optional: Editor-based alternatives

- **VS Code + Cline** (open-source): an in-editor coding agent with planning, terminal usage, file edits, and MCP integration.  
- **Cursor** (proprietary): popular editor with agentic features; keep it as a secondary option to this web UI workflow.

---

## Appendix: Full commands & references

**LM Studio: OpenAI-compatible endpoint** (examples and base URL setting)  
- <https://lmstudio.ai/docs/developer/openai-compat>  
- <https://lmstudio.ai/docs/developer>

**OpenHands + LM Studio quickstart** (model choice, context settings, base URL, Docker run)  
- <https://docs.openhands.dev/openhands/usage/llms/local-llms>

**Docker Desktop networking & host reachability**  
- <https://docs.docker.com/desktop/features/networking/>  
- <https://docs.docker.com/desktop/features/networking/networking-how-tos/>

**Devstral model info / context length**  
- <https://huggingface.co/lmstudio-community/Devstral-Small-2505-GGUF>
