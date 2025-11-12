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

#### Windows 11 Setup

**Step 1: Install LM Studio**
1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai/)
2. Run the installer (`.exe` file)
3. Follow the installation wizard to complete setup
4. Launch LM Studio

**Step 2: Download the Devstral Small 2505 Model**
1. In LM Studio, navigate to the **Discover** tab (search/magnifying glass icon)
2. Search for **"Devstral Small 2505"** by Mistral AI
3. Select the model from the results
4. Choose a quantization level appropriate for your GPU:
   - For RTX 4090 (24GB VRAM): Q5_K_M or Q6_K recommended
   - For lower VRAM: Q4_K_M
5. Click **Download** and wait for completion

**Step 3: Load and Configure the Model**
1. Go to the **Chat** tab (💬 icon)
2. Click **Select a model to load** at the top
3. Choose your downloaded **Devstral Small 2505** model
4. Click the **gear icon** (⚙️) next to the model name to configure settings
5. Apply these **baseline settings for a 4090**:
   - **Context Length:** **32,768** tokens (CRITICAL: set to exactly **32768** or higher; Devstral supports up to **131,072**)
   - **Flash Attention:** **On**
   - **GPU Offload:** **Max** (move all layers to GPU for your quantization)
   - **Offload KV Cache to GPU:** **On** (disable only if you hit VRAM limits with very large contexts)
   - **Keep Model in Memory:** **On**
   - **Try mmap():** **On**
   - **Evaluation Batch Size:** leave default unless you see throttling
   - **RoPE Base/Scale:** **Auto**
6. Click **Load Model** to apply settings

**Step 4: Start the OpenAI-Compatible Server**
1. In LM Studio, go to the **Developer** tab (</> icon)
2. Click **Start Server**
3. Verify the server is running at: `http://localhost:1234/v1`
4. Leave this running in the background

```
http://localhost:1234/v1
```

References: [LM Studio OpenAI-compat endpoints](https://lmstudio.ai/docs/developer/openai-compat), [LM Studio developer docs](https://lmstudio.ai/docs/developer), [Devstral context length](https://huggingface.co/lmstudio-community/Devstral-Small-2505-GGUF)

> **Important:** For long agent runs, keep the model pinned and avoid auto-eviction while OpenHands is active. The **32,768 token context** is critical for proper agent operation—smaller contexts can cause the agent to lose track of its plan.

### 2) OpenHands (web UI)

#### Prerequisites for Windows 11
- **Docker Desktop** must be installed and running
- Ensure Docker Desktop is configured to use WSL 2 backend (Settings → General → Use WSL 2 based engine)
- Verify Docker is working: open PowerShell and run `docker --version`

#### Launch OpenHands with Docker

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

**Windows 11 with Custom Port 3333 (Recommended)**

If port 3000 is busy or you prefer a custom port, use this **PowerShell** command:

```powershell
docker run -it --rm `
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.openhands.dev/openhands/runtime:0.62-nikolaik `
  -e LOG_ALL_EVENTS=true `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -v "$env:USERPROFILE\.openhands:/.openhands" `
  -p 3333:3000 `
  --add-host host.docker.internal:host-gateway `
  --name openhands-app `
  docker.openhands.dev/openhands/openhands:0.62
```

**Important PowerShell syntax notes:**
- Use backtick (`` ` ``) for line continuation (NOT backslash `\`)
- Use `$env:USERPROFILE` to access the user profile directory (equivalent to `~` in Bash)
- Ensure all lines except the last end with a backtick
- Run in PowerShell (not CMD)

Then open in your browser:

```
http://localhost:3333
```

**Alternative: Bash / Linux / WSL with Custom Port:**

```bash
docker run -it --rm \
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.openhands.dev/openhands/runtime:0.62-nikolaik \
  -e LOG_ALL_EVENTS=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$HOME/.openhands":"/.openhands" \
  -p 3333:3000 \
  --add-host host.docker.internal:host-gateway \
  --name openhands-app \
  docker.openhands.dev/openhands/openhands:0.62
```

> **Networking note:** On Docker Desktop (Windows/Mac), `host.docker.internal` lets the container reach services on your host machine (e.g., LM Studio at `http://host.docker.internal:1234/v1`). The `--add-host host.docker.internal:host-gateway` flag ensures this works correctly.
>
> **Port mapping:** `-p 3333:3000` maps port 3000 inside the container to port 3333 on your host. Access the UI at `http://localhost:3333`.

References: [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/), [How-tos](https://docs.docker.com/desktop/features/networking/networking-how-tos/), [OpenHands Local LLMs guide](https://docs.openhands.dev/openhands/usage/llms/local-llms)

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

## Connect GitHub to OpenHands

To enable OpenHands to interact with your GitHub repositories (clone, create branches, open PRs, etc.), you need to configure GitHub integration.

### Step 1: Create a GitHub Personal Access Token (PAT)

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
   - Direct link: [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token** → **Generate new token (classic)**
3. Give it a descriptive name (e.g., "OpenHands Local Agent")
4. Set expiration as needed (e.g., 90 days, or "No expiration" for convenience)
5. Select the following **scopes** (permissions):
   - ✅ **repo** (Full control of private repositories) - Required for repository access
   - ✅ **workflow** (Update GitHub Action workflows) - Optional, needed for CI/CD operations
   - ✅ **read:org** (Read org and team membership) - Optional, for organization repositories
6. Click **Generate token** at the bottom
7. **IMPORTANT:** Copy the token immediately (it won't be shown again)

### Step 2: Configure GitHub in OpenHands

1. In the OpenHands web UI, click the **Settings** icon (⚙️) in the top-right corner
2. Navigate to **Settings** → **GitHub**
3. Paste your Personal Access Token in the **GitHub Token** field
4. Click **Save** or **Connect**
5. Verify the connection is successful (you should see a green checkmark or success message)

### Step 3: Select a Repository

1. In the OpenHands main interface, you can now select a GitHub repository to work on
2. OpenHands will clone the repository and allow the agent to make changes
3. The agent can create branches, commit changes, and open pull requests on your behalf

### Security Best Practices

- **Never share your GitHub token** with anyone or commit it to a repository
- Use tokens with minimal required permissions for your use case
- Set token expiration dates and rotate them regularly
- Consider using fine-grained personal access tokens (beta) for more granular control
- Store tokens securely (e.g., in a password manager)
- Revoke tokens immediately if compromised: [https://github.com/settings/tokens](https://github.com/settings/tokens)

### Troubleshooting GitHub Integration

- **"Authentication failed"**: Regenerate your token and ensure you've selected the correct scopes
- **"Repository not found"**: Verify the token has access to the repository (check organization settings if applicable)
- **"Permission denied"**: Ensure the token has the `repo` scope enabled
- **Token expired**: Generate a new token and update it in OpenHands settings

Reference: [OpenHands: GitHub Setup](https://docs.openhands.dev/openhands/usage/settings/integrations-settings#github-setup)

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
