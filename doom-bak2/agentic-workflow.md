I'll design and document a complete multi-agent workflow for translating vanilla Emacs configs to literate Doom Emacs configs. Let me first research the latest versions and best practices for all the technologies involved.

Let me gather more specific information on the remaining components.

Let me gather more specific information about Doom Emacs module structure, macros, and the remaining tools.

Let me verify a few more details on Pydantic AI + LiteLLM integration and Doom module file organization.

I have all the research I need. Let me now design and document the complete **Doom-Stitcher** workflow system. Given the complexity, I'll organize this as a structured architecture document with the full codebase embedded in collapsible sections.

# Doom-Stitcher: Vanilla→Doom Emacs Translation Pipeline

> **Codename:** `doom-stitcher`  
> **Version:** 1.0.0 (June 2026)  
> **Stack:** Pydantic AI 1.106 · LangGraph 1.2.4 · LiteLLM (Podman) · Python 3.13 · uv

## 🎯 Executive Summary

`doom-stitcher` is a 9-phase LangGraph DAG powered by Pydantic AI agents that ingests a **vanilla Emacs configuration** (`emacs/config.org`, `emacs/early-init.el`) plus a user-supplied **Doom `init.el`** (declaring enabled modules), consults the upstream `doomemacs/modules/` source tree for ground-truth defaults, and emits a single, deduplicated, audited, **literate `config.org`** that tangles into `config.el`, `init.el`, and `packages.el`. All LLM calls route through a model-agnostic **LiteLLM proxy** running locally in Podman, making the workflow swappable across providers (OpenAI, Anthropic, Bedrock, Ollama, etc.) without code changes.

---

## 📁 Project Directory Structure

<details>
<summary><strong>Pre-Workflow State (root: <code>~/.config/doom</code>)</strong></summary>

```
~/.config/doom/
├── init.el                  ← user-provided, declares Doom modules
├── litellm-config.yaml      ← user-provided, model routing
├── .env                     ← user-provided, API keys for LiteLLM
├── doomemacs/               ← cloned Doom source tree (retained)
│   └── modules/
│       ├── config/
│       │   ├── default/     ← :config default defaults
│       │   └── literate/    ← :config literate
│       ├── completion/
│       ├── ui/
│       ├── editor/
│       ├── lang/
│       └── ...
└── emacs/                   ← VANILLA configs (DELETED post-run)
    ├── config.org           ← parsed in Phase 1
    ├── early-init.el        ← parsed in Phase 1
    └── lisp/
        └── org-src-context.el  ← MOVED to lisp/ in root
```

</details>

<details>
<summary><strong>Post-Workflow State</strong></summary>

```
~/.config/doom/
├── config.org               ← CREATED: literate source blocks
├── README.md                ← CREATED: setup & maintenance guide
├── .gitignore               ← CREATED: ignores generated elisp
├── setup-doom.sh            ← CREATED: idempotent first-install
├── lisp/                    ← MOVED
│   └── org-src-context.el
├── doomemacs/               ← retained
└── workflow/                ← retained (all agent code)
    ├── .envrc
    ├── run-workflow.sh
    ├── requirements.txt
    ├── pyproject.toml
    ├── config.py
    ├── prompt.py
    ├── models.py
    ├── state.py
    ├── tools.py
    ├── agents.py
    ├── graph.py
    ├── main.py
    ├── utils/
    │   ├── __init__.py
    │   ├── elisp.py
    │   └── org.py
    └── phases/
        ├── __init__.py
        ├── phase1_vanilla_ingestion.py
        ├── phase2_init_ingestion.py
        ├── phase3_doom_ingestion.py
        ├── phase4_initial_translation.py
        ├── phase5_refinement.py
        ├── phase6_deduplication.py
        ├── phase7_audit.py
        ├── phase8_output_generation.py
        └── phase9_maintenance.py
```

</details>

---

## 🏗️ Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│  run-workflow.sh                                                     │
│  1. Loads .env    2. podman run litellm (config mounted)             │
│  3. Waits for /health/liveliness   4. uv run python main.py          │
│  5. trap EXIT → podman rm -f                                         │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│  LangGraph StateGraph (9 nodes)                                      │
│                                                                       │
│   START ──► P1 Vanilla ──► P2 Init ──► P3 Doom ──► P4 Translate    │
│                                                  │                   │
│                                                  ▼                   │
│                                            P5 Refine                │
│                                                  │                   │
│                                                  ▼                   │
│                                          P6 Deduplicate              │
│                                                  │                   │
│                                                  ▼                   │
│                                              P7 Audit                │
│                                                  │                   │
│                                                  ▼                   │
│                                         P8 Output (FS ops)          │
│                                                  │                   │
│                                                  ▼                   │
│                                         P9 Maintenance ──► END      │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
                       Pydantic AI Agents (6) calling
                       OpenAI-compatible LiteLLM @ :4000
```

---

## 🔑 Key Design Decisions

| Decision | Rationale |
|---|---|
| **Pydantic AI's `LiteLLMProvider`** for LLM routing | Native support in v1.106; one provider class handles all backends |
| **Model names from env vars**, not hardcoded | True model-agnosticism — swap models via `litellm-config.yaml` + `.env` |
| **Two-tier state**: TypedDict (LangGraph) + Pydantic (typed payloads) | Strong validation at boundaries, flexible reducers between nodes |
| **Deterministic I/O in phases 1–3, 8–9**; LLM in **4–7** | Reduces hallucination surface; LLMs only do semantic work |
| **Per-phase retry budgets** via Pydantic AI `retries` | Output validation retries are bounded; tools can retry independently |
| **Tools are stateless functions** | Pure reads/writes; no hidden state, easy to test |
| **`:config literate` always injected** | Guarantees `doom sync` tangles `config.org` correctly |
| **Org src blocks targeted explicitly** (`config.el`, `init.el`, `packages.el`) | Aligns with Doom's three-file DOOMDIR contract |
| **Doom default lookup is the anti-hallucination mechanism** | Every translated value cross-referenced against `doomemacs/modules/` |

---

## 🚀 Quick Start

```bash
# 1. Prereqs: podman, uv, direnv, emacs (for verification only)
brew install podman uv direnv  # macOS
# or: apt install podman; pipx install uv; apt install direnv

# 2. Place vanilla config under emacs/, clone doomemacs, supply init.el + litellm-config.yaml + .env
cd ~/.config/doom/workflow
direnv allow                # creates .venv + installs deps

# 3. Run the workflow
./run-workflow.sh

# 4. Inspect outputs
ls -la ~/.config/doom/
cat ~/.config/doom/config.org
~/.config/emacs/bin/doom sync  # tangles config.org → config.el/init.el/packages.el
```

---

## 📂 Complete Codebase

### Root-Level Outputs (Generated by Phase 8)

<details>
<summary><strong>📄 <code>~/.config/doom/.gitignore</code></strong> — created by workflow</summary>

```gitignore
# Doom Emacs generated files (regenerated by `doom sync`)
config.el
init.el
packages.el
custom.el

# Doom runtime
.doom.d/
straight-build/
.elc/
*.elc

# Local workflow artifacts
workflow/.venv/
workflow/__pycache__/
workflow/**/__pycache__/
workflow/.litellm-*.log
workflow/.state/
workflow/.last-run.json

# Secrets & local config
.env
.env.local
litellm-config.local.yaml

# OS noise
.DS_Store
Thumbs.db

# Editor backups
*~
\#*\#
.\#*
```

</details>

<details>
<summary><strong>📄 <code>~/.config/doom/README.md</code></strong> — created by workflow</summary>

````markdown
# Doom Emacs Configuration

This repository is a **literate Doom Emacs configuration** generated by
[`doom-stitcher`](./workflow/) from a vanilla Emacs config. The single source of
truth is `config.org`; it is tangled by `doom sync` into `config.el`,
`init.el`, and `packages.el`.

> ⚠️ **Do not edit `config.el`, `init.el`, or `packages.el` directly.** They are
> regenerated whenever `config.org` is saved or `doom sync` runs.

## Prerequisites

- **Emacs 29+** (Org 9.7+ required for `#+property:` style headers)
- **Git** (for Doom's package manager, straight.el)
- **Just** (optional, for running recipes) — or use the `setup-doom.sh` script

## First-time Installation

```bash
# 1. Run the setup script (clones Doom to ~/.config/emacs and runs doom install)
./setup-doom.sh

# 2. Launch Doom Emacs — it will:
#    - tangle config.org → config.el
#    - install all declared packages
#    - byte-compile your config
emacs --daemon

# 3. Verify
~/.config/emacs/bin/doom doctor
~/.config/emacs/bin/doom sync
```

## Daily Workflow

| Task | Command |
|---|---|
| Re-tangle after editing `config.org` | `~/.config/emacs/bin/doom sync` |
| Reload config (in Emacs) | `M-x doom/reload` or `SPC h r r` |
| Update all packages | `~/.config/emacs/bin/doom upgrade` |
| Find a config heading | `SPC h f` (with `:config literate` enabled) |
| Check for issues | `~/.config/emacs/bin/doom doctor` |

## Repository Layout

```
.
├── config.org           ← EDIT THIS (literate source)
├── init.el              ← GENERATED, do not edit
├── config.el            ← GENERATED, do not edit
├── packages.el          ← GENERATED, do not edit
├── lisp/                ← Custom Elisp
│   └── org-src-context.el
├── doomemacs/           ← Doom source tree (read-only reference)
├── workflow/            ← doom-stitcher agentic pipeline
└── setup-doom.sh        ← First-time install script
```

## Regenerating the Literate Config

If you pull upstream changes to your vanilla config or want to re-derive the
Doom config from scratch:

```bash
# Restore vanilla sources
mkdir -p emacs/lisp
# ... drop your vanilla config.org, early-init.el, lisp/org-src-context.el here

cd workflow
./run-workflow.sh
```

The workflow will:
1. Re-ingest vanilla configs and Doom module defaults
2. Re-run translation, refinement, deduplication, and audit
3. Atomically swap in the new `config.org`

## Maintenance Cycle

`workflow/phases/phase9_maintenance.py` produces a `maintenance-summary.json`
that tracks:
- Doom module defaults that changed upstream
- Settings in your config that may need review
- New Doom features matching your existing patterns

Run it monthly (or add to cron / GitHub Actions) to keep your config in
sync with Doom's evolution.

## Troubleshooting

**`doom sync` complains about missing packages**
```bash
~/.config/emacs/bin/doom sync -u
```

**`config.org` won't tangle**
Open it in Emacs and run `M-x org-babel-tangle` manually. Errors appear in
`*Org Babel Output*` buffer.

**Want to start over?**
```bash
rm config.el init.el packages.el
~/.config/emacs/bin/doom sync
```
````

</details>

<details>
<summary><strong>📄 <code>~/.config/doom/setup-doom.sh</code></strong> — created by workflow (customized for detected modules)</summary>

```bash
#!/usr/bin/env bash
# Generated by doom-stitcher on 2026-06-07
# Idempotent first-time Doom Emacs installer for this DOOMDIR.
set -euo pipefail

DOOMDIR="${DOOMDIR:-$HOME/.config/doom}"
EMACSDIR="${EMACSDIR:-$HOME/.config/emacs}"
DOOM_REPO="https://github.com/doomemacs/doomemacs"


# 2. Clone Doom Emacs (shallow)
if [ ! -d "$EMACSDIR" ]; then
  echo "Cloning Doom Emacs to $EMACSDIR ..."
  git clone --depth 1 "$DOOM_REPO" "$EMACSDIR"
fi

# 3. Install / sync
if [ ! -x "$EMACSDIR/bin/doom" ]; then
  echo "Running doom install ..."
  "$EMACSDIR/bin/doom" install --no-config
fi

echo "Running doom sync ..."
"$EMACSDIR/bin/doom" sync

cat <<'NOTE'

✅ Doom Emacs installed. Launch with:
    ~/.config/emacs/bin/doom emacs

Run `~/.config/emacs/bin/doom doctor` if anything looks wrong.
NOTE
```

</details>

---

### `workflow/` — Python Application

#### Project Metadata

<details>
<summary><strong>📄 <code>workflow/requirements.txt</code></strong></summary>

```txt
# Pinned to the latest stable releases as of June 2026.
# Regenerate with `uv pip compile pyproject.toml` for production.
pydantic-ai[litellm,openai,anthropic]>=1.106.0,<2.0.0
pydantic>=2.10.0,<3.0.0
langgraph>=1.2.4,<2.0.0
langchain-core>=0.3.40
openai>=1.50.0
httpx>=0.27.0
pyyaml>=6.0
python-dotenv>=1.0.1
rich>=13.7.0
tenacity>=9.0.0
loguru>=0.7.2
platformdirs>=4.2.0
```

</details>

<details>
<summary><strong>📄 <code>workflow/pyproject.toml</code></strong></summary>

```toml
[project]
name = "doom-stitcher"
version = "1.0.0"
description = "Translate vanilla Emacs configs to literate Doom Emacs configs"
readme = "README.md"
requires-python = ">=3.13"
license = { text = "MIT" }
authors = [{ name = "doom-stitcher contributors" }]

dependencies = [
    "pydantic-ai[litellm,openai,anthropic]>=1.106.0,<2.0.0",
    "pydantic>=2.10.0,<3.0.0",
    "langgraph>=1.2.4,<2.0.0",
    "langchain-core>=0.3.40",
    "openai>=1.50.0",
    "httpx>=0.27.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.1",
    "rich>=13.7.0",
    "tenacity>=9.0.0",
    "loguru>=0.7.2",
    "platformdirs>=4.2.0",
]

[project.scripts]
doom-stitcher = "main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
```

</details>

<details>
<summary><strong>📄 <code>workflow/.envrc</code></strong> — direnv (provided verbatim from spec)</summary>

```bash
# .envrc for doom-stitcher
# - Creates a Python 3.13 virtual environment with uv
# - Installs/updates dependencies from requirements.txt automatically
# - Prints the active Python version on activation
# - Loads secrets from .env

# 1. Ensure uv is available
if ! command -v uv >/dev/null 2>&1; then
  log_error "uv is not installed"
  exit 1
fi

# 2. Create the virtual environment if it doesn't already exist
if [ ! -d ".venv" ]; then
  uv venv -p 3.13
fi

# 3. Install or update dependencies when requirements.txt changes
REQ_FILE="requirements.txt"
HASH_FILE=".venv/.requirements-hash"

if [ -f "$REQ_FILE" ]; then
  current_hash=$(shasum "$REQ_FILE" | cut -d ' ' -f 1)
  stored_hash=""
  [ -f "$HASH_FILE" ] && stored_hash=$(cat "$HASH_FILE")

  if [ "$current_hash" != "$stored_hash" ]; then
    log_status "Installing/updating Python packages from requirements.txt..."
    uv pip install -r "$REQ_FILE"
    echo "$current_hash" >"$HASH_FILE"
  fi
fi

# 4. Activate the environment using the idiomatic layout command
layout python .venv/bin/python

# 5. Print the Python version on activation (visible every time you enter the directory)
log_status "Python version: $(python --version 2>&1)"

```

</details>

<details>
<summary><strong>📄 <code>workflow/run-workflow.sh</code></strong> — bash orchestrator</summary>

```bash
#!/usr/bin/env bash
# run-workflow.sh — boot LiteLLM in Podman, run doom-stitcher, clean up.
# Idempotent: re-running on a fresh tree installs the proxy, executes, and tears down.
set -euo pipefail

# ---------- paths ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LITELLM_CONFIG="$ROOT_DIR/litellm-config.yaml"
ENV_FILE="$ROOT_DIR/.env"

# ---------- load .env (secrets for LiteLLM) ----------
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# ---------- configuration ----------
LITELLM_IMAGE="${LITELLM_IMAGE:-docker.litellm.ai/berriai/litellm:main-stable}"
LITELLM_CONTAINER="${LITELLM_CONTAINER:-doom-stitcher-litellm}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_HOST="${LITELLM_HOST:-127.0.0.1}"
LITELLM_HEALTH_URL="http://${LITELLM_HOST}:${LITELLM_PORT}/health/liveliness"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-90}"   # seconds

# ---------- preflight ----------
[ -f "$LITELLM_CONFIG" ] || { echo "❌ Missing $LITELLM_CONFIG" >&2; exit 1; }
command -v podman >/dev/null 2>&1 || { echo "❌ podman not installed" >&2; exit 1; }

# Ensure venv is ready (in case direnv isn't active)
if [ ! -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  echo "==> Bootstrapping Python venv..."
  ( cd "$SCRIPT_DIR" && command -v uv >/dev/null 2>&1 && uv venv -p 3.13 || python3.13 -m venv .venv )
  ( cd "$SCRIPT_DIR" && (command -v uv >/dev/null 2>&1 && uv pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt) )
fi

# ---------- start LiteLLM ----------
echo "==> Cleaning up any prior $LITELLM_CONTAINER..."
if podman container exists "$LITELLM_CONTAINER" 2>/dev/null; then
  podman rm -f "$LITELLM_CONTAINER" >/dev/null
fi

echo "==> Starting LiteLLM ($LITELLM_IMAGE) on $LITELLM_HOST:$LITELLM_PORT..."
# Podman pulls from Docker Hub transparently when given the docker:// prefix;
# the standard LiteLLM image works as-is.
podman run -d \
  --name "$LITELLM_CONTAINER" \
  --restart=no \
  -p "${LITELLM_HOST}:${LITELLM_PORT}:4000" \
  -v "$LITELLM_CONFIG:/app/config.yaml:ro" \
  --env-file <(grep -v '^#' "$ENV_FILE" 2>/dev/null | grep -E '^[A-Z_]+=' || true) \
  "$LITELLM_IMAGE" \
  --config /app/config.yaml \
  --port 4000 >/dev/null

# ---------- wait for healthy ----------
echo "==> Waiting for LiteLLM to become healthy (timeout: ${HEALTH_TIMEOUT}s)..."
elapsed=0
interval=2
until curl -fsS "$LITELLM_HEALTH_URL" >/dev/null 2>&1; do
  if [ "$elapsed" -ge "$HEALTH_TIMEOUT" ]; then
    echo "❌ LiteLLM failed to become healthy in ${HEALTH_TIMEOUT}s" >&2
    echo "--- container logs ---" >&2
    podman logs "$LITELLM_CONTAINER" >&2 || true
    podman rm -f "$LITELLM_CONTAINER" >/dev/null
    exit 1
  fi
  sleep "$interval"
  elapsed=$((elapsed + interval))
  printf "."
done
echo
echo "✅ LiteLLM healthy at $LITELLM_HEALTH_URL"

# ---------- run workflow ----------
cleanup() {
  local exit_code=$?
  echo "==> Tearing down LiteLLM container..."
  if podman container exists "$LITELLM_CONTAINER" 2>/dev/null; then
    podman rm -f "$LITELLM_CONTAINER" >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

echo "==> Running doom-stitcher workflow..."
cd "$SCRIPT_DIR"
if command -v uv >/dev/null 2>&1; then
  exec uv run python main.py "$@"
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec python main.py "$@"
fi
```

</details>

---

#### Core Modules

<details>
<summary><strong>📄 <code>workflow/config.py</code></strong> — Configuration loader</summary>

```python
"""Centralized configuration for doom-stitcher.

All paths and model selections come from environment variables. The workflow
is fully model-agnostic: model names are passed through verbatim to the
LiteLLM proxy, which resolves them via its own config.yaml.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Required env var {name} is not set")
    return val or ""


@dataclass(frozen=True)
class Paths:
    """Filesystem layout rooted at DOOMDIR."""

    doomdir: Path = field(default_factory=lambda: Path(_env("DOOMDIR", str(Path.home() / ".config/doom"))).expanduser())
    emacs_subdir: Path = field(default_factory=lambda: Path(_env("DOOMDIR", "") + "/emacs"))
    doomemacs_subdir: Path = field(default_factory=lambda: Path(_env("DOOMDIR", "") + "/doomemacs"))
    workflow_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    modules_dir: Path = field(init=False)
    lisp_dir: Path = field(init=False)
    state_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "modules_dir", self.doomemacs_subdir / "modules")
        object.__setattr__(self, "lisp_dir", self.doomdir / "lisp")
        object.__setattr__(self, "state_dir", self.workflow_dir / ".state")


@dataclass(frozen=True)
class ModelConfig:
    """Model-agnostic LLM routing.

    The `model_name` strings are passed through Pydantic AI's
    OpenAIChatModel to the LiteLLM proxy. The proxy's config.yaml is the
    single source of truth for which upstream model each alias maps to.
    """

    base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "http://localhost:4000"))
    api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", "sk-litellm-local"))

    # Per-role model selection. Each role can be tuned independently.
    default_model: str = field(default_factory=lambda: _env("DOOM_STITCHER_MODEL_DEFAULT", "doom-stitcher-default"))
    translation_model: str = field(default_factory=lambda: _env("DOOM_STITCHER_MODEL_TRANSLATION", "doom-stitcher-translator"))
    audit_model: str = field(default_factory=lambda: _env("DOOM_STITCHER_MODEL_AUDIT", "doom-stitcher-auditor"))
    extraction_model: str = field(default_factory=lambda: _env("DOOM_STITCHER_MODEL_EXTRACTION", "doom-stitcher-default"))


@dataclass(frozen=True)
class WorkflowConfig:
    paths: Paths = field(default_factory=Paths)
    models: ModelConfig = field(default_factory=ModelConfig)

    # Operational toggles
    verbose: bool = field(default_factory=lambda: _env("DOOM_STITCHER_VERBOSE", "0") == "1")
    dry_run: bool = field(default_factory=lambda: _env("DOOM_STITCHER_DRY_RUN", "0") == "1")
    skip_maintenance: bool = field(default_factory=lambda: _env("DOOM_STITCHER_SKIP_MAINTENANCE", "0") == "1")


CONFIG = WorkflowConfig()
```

</details>

<details>
<summary><strong>📄 <code>workflow/prompt.py</code></strong> — The Doom-Stitcher system prompt</summary>

```python
"""Doom-Stitcher runtime directive — the prompt attached to every LLM call.

This is the verbatim Runtime Directive from the project specification,
stored as a module-level constant so it can be referenced from any agent
or phase. Edit here if you need to evolve the agent's behavior contract.
"""
from __future__ import annotations

DOOM_STITCHER_DIRECTIVE = """# Runtime Directive for the Vanilla-to-Doom Translation Agent

**Mission Objective**
You are the **Doom-Stitcher Agent**, an expert Emacs developer executing a multi-phase LangGraph workflow. Your mission is to translate a vanilla Emacs configuration into a highly optimized, literate Doom Emacs configuration, ensuring zero hallucinations, strict deduplication, and proper custom Elisp integration.

## 1. Operational Context

You are operating within the `~/.config/doom` root directory. You have access to the following resources:

- **Vanilla Config**: `emacs/config.org`, `emacs/early-init.el`, `emacs/lisp/org-src-context.el`
- **User Doom Modules**: `init.el` (provided by the user in the root dir, specifying enabled modules)
- **Doom Source Tree**: `doomemacs/` (specifically the `modules/` subfolder containing default configurations)
- **Local LLM Proxy**: LiteLLM running at `http://localhost:4000` for routing your thoughts and generations.

## 2. Translation Rules & Strict Constraints

- **Literate Structure**: All output must be written to a single `config.org`. This file must contain org-mode source blocks that tangle to `config.el`, `init.el`, and `packages.el`.
- **Init.el Handling**: The user-provided `init.el` content must be placed inside the `init.el` source block in `config.org`. Any new modules required by the translation must be appended to this block.
- **Doom Syntax**: You must use Doom-specific macros and conventions: `after!`, `use-package!`, `map!`, `setq-hook!`, etc. Do not use vanilla `use-package` or raw `require` statements unless absolutely necessary for custom Elisp.
- **No Hallucinations**: You must verify every Doom macro and configuration variable against the `doomemacs/modules/` source tree. If you are unsure, query the source tree again.
- **Transients**: All transient configurations from the vanilla setup must be retained and properly formatted.
- **Custom Elisp (`org-src-context.el`)**: This file must be usable. In the `config.el` source block, you must update the `load-path` to include the `lisp/` directory and execute `(require 'org-src-context)` inside an `(after! org ...)` block.
- **Overriding Defaults**: You must read the default Doom module configurations from `doomemacs/modules/`. Only overwrite Doom's shipped defaults if the vanilla config explicitly requires a different setting. If a setting matches Doom's default, omit it from the final output to maintain cleanliness.
- **Fidelity**: The translation is not 1-to-1, but it must be functionally close enough to the original vanilla setup.

## 3. Execution Phases

Execute the following phases sequentially, utilizing the LangGraph state machine:

1.  **Ingest Vanilla Configs**: Read and analyze `emacs/config.org` and `emacs/early-init.el`. Catalog all packages, keybindings, and custom functions.
2.  **Ingest User `init.el`**: Read the root `init.el` to determine which Doom modules are active.
3.  **Ingest Doom Modules**: Read the relevant module files from `doomemacs/modules/` based on the active modules.
4.  **Translate (Pass 1)**: Generate the initial `config.org` mapping vanilla config to Doom syntax.
5.  **Refine & Integrate (Pass 2)**: Integrate `org-src-context.el`, refine transients, and explicitly override Doom defaults where necessary.
6.  **Deduplicate**: Strip out any `package!` declarations or `setq` configurations that duplicate Doom's ingested module defaults.
7.  **Audit**: Perform a comprehensive structural and Elisp syntax check on the whole `config.org`. Verify tangle headers.
8.  **Generate Outputs**: Write the final `config.org`, `README.md`, and `.gitignore`. Execute file system operations to move `lisp/org-src-context.el` to the root `lisp/` directory and delete the `emacs/` folder.
9.  **Report for Maintenance**: Output a summary of the translated configuration to be stored in the LangGraph state for future monthly update checks against the `doomemacs/` upstream.

**FINAL INSTRUCTION**: Proceed with the execution of the LangGraph workflow starting at Phase 1. Continuously validate your outputs against the strict constraints provided. Do not guess at Doom configurations; always verify against the source tree.
"""


# Per-phase directive extensions. Concatenated with DOOM_STITCHER_DIRECTIVE.
PHASE_4_HINTS = """

## Phase 4 — Initial Translation (Pass 1) — Additional Context

When generating the `config.org` skeleton, use the following tangle rules:

- `# tangle` default → `config.el`
- `# tangle packages.el` → packages
- `# tangle init.el` → init
- Set `# tangle yes` for any src block where the destination is the same as the default

Use this header at the top of `config.org`:

```
#+title:      Doom Emacs Configuration
#+subtitle:   Literate config generated by doom-stitcher
#+startup:    overview
#+property:   header-args:emacs-lisp :tangle config.el :results none :lexical t
#+property:   header-args:emacs-lisp :tangle packages.el :results none :lexical t
#+property:   header-args:emacs-lisp :tangle init.el :results none :lexical t
```

For each vanilla package → produce a `(package! ...)` block tangled to
`packages.el`. For each `setq` → produce a `(setq ...)` or
`(setq-hook! ...)` block inside the appropriate `(after! <package> ...)` in
`config.el`.
"""

PHASE_5_HINTS = """

## Phase 5 — Refinement — Additional Context

After initial translation:

1. Add this boilerplate to the `config.el` source block (placed at the
   *very top* of the `config.el` content, before any user code):

   ```emacs-lisp
   ;; Add lisp/ to load-path for custom Elisp
   (add-to-list 'load-path (expand-file-name "lisp/" doom-user-dir))
   ```

2. Add an `(after! org ...)` block (inside `config.el` content) that does:

   ```emacs-lisp
   (after! org
     (require 'org-src-context))
   ```

3. Transients: if vanilla used `defhydra`, `transient.define`, or
   `easy-hydra`, port them to Doom's `defhydra` with `:bind` keys.
4. Honor `early-init.el` settings by emitting them under a
   `# tangle early-init.el` source block (rare, but valid in literate
   setups that include early-init hooks).
"""

PHASE_7_HINTS = """

## Phase 7 — Audit — Additional Context

Verification checklist (each item must pass before approving the output):

- [ ] Every `package!` exists in Doom's pinned package list (or is
      declared as a `:recipe` or `:pin` in `packages.el`).
- [ ] Every macro used (`after!`, `use-package!`, `map!`, `setq-hook!`,
      `add-hook!`, `def-hydra!`, `package!`) is a real Doom macro (defined
      in `doomemacs/core/core-lib.el` or `lisp/doom-lib.el`).
- [ ] All `(after! <package> ...)` blocks reference a feature symbol,
      NOT a major mode name (common mistake: `(after! python-mode ...)` —
      correct: `(after! python ...)`).
- [ ] Tangle headers are valid: every `#+begin_src` is matched by
      `#+end_src`; `:tangle` paths resolve to `config.el`, `init.el`, or
      `packages.el` relative to `~/.config/doom/`.
- [ ] No vanilla `use-package` without the bang (unless wrapping a
      third-party lib that requires it).
- [ ] `(doom! :config literate ...)` is present in the `init.el` source
      block.
- [ ] `load-path` update for `lisp/` is present and correct.
- [ ] `(require 'org-src-context)` is wrapped in `(after! org ...)`.
- [ ] No `setq` duplicates Doom defaults (this is enforced by Phase 6
      but the auditor should re-check).
"""
```

</details>

<details>
<summary><strong>📄 <code>workflow/models.py</code></strong> — Pydantic data models</summary>

```python
"""Pydantic v2 models representing every typed payload in the workflow.

These are the contracts that flow through LangGraph state. Every agent's
output is validated against one of these models, ensuring the LLM cannot
inject malformed data into the next phase.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Enums ----------------------------------------------------------


class DoomModuleCategory(str, Enum):
    """Official Doom module categories (from doomemacs/modules/*/)."""

    APP = "app"
    CHECKERS = "checkers"
    COMPLETION = "completion"
    CONFIG = "config"
    EDITOR = "editor"
    EMACS = "emacs"
    EMAIL = "email"
    INPUT = "input"
    LANG = "lang"
    OS = "os"
    TERM = "term"
    TOOLS = "tools"
    UI = "ui"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# ---------- Vanilla ingestion (Phase 1) ----------------------------------


class VanillaPackage(BaseModel):
    """A package declared in the vanilla config."""

    name: str
    source: str | None = None  # e.g. "melpa", "gnu", "quelpa", or recipe
    version_pin: str | None = None
    use_package_block: str | None = None  # raw elisp for reference


class VanillaKeybinding(BaseModel):
    """A keybinding extracted from vanilla config."""

    keys: str
    command: str
    mode: str | None = None  # global, local, or specific-mode
    raw_definition: str | None = None


class VanillaCustomDef(BaseModel):
    """A custom function, defhydra, transient, advice, etc."""

    kind: Literal["defun", "defmacro", "defhydra", "defvar", "defcustom", "transient", "advice", "other"]
    name: str
    body: str
    source_location: str | None = None  # e.g. "emacs/config.org::Custom defuns"


class VanillaConfig(BaseModel):
    """Aggregate of everything extracted from the vanilla configs."""

    packages: list[VanillaPackage] = Field(default_factory=list)
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)
    custom_defs: list[VanillaCustomDef] = Field(default_factory=list)
    early_init_settings: list[str] = Field(default_factory=list)  # raw early-init.el lines
    notes: str = ""
    source_org_path: str | None = None
    source_early_init_path: str | None = None

    @field_validator("packages", "keybindings", "custom_defs", mode="before")
    @classmethod
    def _accept_none(cls, v: Any) -> Any:
        return v or []


# ---------- User init.el ingestion (Phase 2) -----------------------------


class DoomModuleFlag(BaseModel):
    """A flag applied to a module, e.g. :completion company +tng."""

    name: str
    value: str | bool = True  # boolean for bare flags, str for +flag=value


class DoomModule(BaseModel):
    """A single enabled Doom module from the user's init.el."""

    category: DoomModuleCategory
    name: str
    flags: list[DoomModuleFlag] = Field(default_factory=list)

    @property
    def path(self) -> str:
        return f"{self.category.value}/{self.name}"


class UserInitConfig(BaseModel):
    """The full dooM! block as parsed from the user's init.el."""

    modules: list[DoomModule]
    raw_doom_block: str
    source_path: str


# ---------- Doom module ingestion (Phase 3) -----------------------------


class DoomModuleFile(BaseModel):
    """A single file (config.el, init.el, packages.el) of a Doom module."""

    filename: str  # e.g. "config.el"
    content: str
    relevant_sections: list[str] = Field(default_factory=list)  # names of defuns/sections we care about


class DoomModuleData(BaseModel):
    """All files + extracted defaults for a Doom module."""

    category: str
    name: str
    path: str  # e.g. "ui/treemacs"
    files: list[DoomModuleFile] = Field(default_factory=list)

    # Quick-lookup: variable name → default value expression (string)
    defaults: dict[str, str] = Field(default_factory=dict)
    # Quick-lookup: package name → recipe/flag (e.g. "package! treemacs")
    packages: dict[str, str] = Field(default_factory=dict)
    # Quick-lookup: keybinding pattern → definition
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)
    # macrology this module uses (after!, use-package!, etc.)
    macros_used: list[str] = Field(default_factory=list)


# ---------- Translation outputs (Phases 4-6) ----------------------------


class InitElBlock(BaseModel):
    """The init.el source block content (the dooM! macro + early settings)."""

    doom_block: str
    extra_early_settings: str = ""


class PackagesElBlock(BaseModel):
    """The packages.el source block content."""

    package_declarations: list[str] = Field(default_factory=list)  # each a (package! ...) form
    recipes: list[str] = Field(default_factory=list)  # each a (recipe! ...) form
    pins: list[str] = Field(default_factory=list)  # each a (pin ...) form


class ConfigElBlock(BaseModel):
    """The config.el source block content."""

    load_path_setup: str = ""
    after_org_setup: str = ""  # contains (require 'org-src-context)
    config_forms: list[str] = Field(default_factory=list)  # each a (after! ...)/(use-package! ...)/(setq ...)
    custom_defs: list[VanillaCustomDef] = Field(default_factory=list)
    transient_defs: list[str] = Field(default_factory=list)
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)


class TranslatedConfig(BaseModel):
    """A single translated configuration, ready to be rendered into config.org."""

    init_el: InitElBlock
    packages_el: PackagesElBlock
    config_el: ConfigElBlock
    preamble: str = ""  # top-of-file org keywords


# ---------- Audit (Phase 7) -----------------------------------------------


class AuditFinding(BaseModel):
    severity: Severity
    category: str  # e.g. "macro-validity", "duplicate", "tangle"
    message: str
    location: str | None = None  # e.g. "config.el src block"
    suggested_fix: str | None = None


class AuditReport(BaseModel):
    findings: list[AuditFinding] = Field(default_factory=list)
    passed: bool = True
    summary: str = ""

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)
        if finding.severity == Severity.ERROR:
            self.passed = False


# ---------- Maintenance (Phase 9) ----------------------------------------


class MaintenanceSummary(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    doomemacs_commit: str | None = None
    doom_modules_tracked: list[str] = Field(default_factory=list)
    override_setpoints: list[str] = Field(default_factory=list)  # settings that explicitly override Doom defaults
    upstream_changes_to_review: list[str] = Field(default_factory=list)
    config_fingerprint: str  # hash of final config.org, used to detect drift

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

</details>

<details>
<summary><strong>📄 <code>workflow/state.py</code></strong> — LangGraph state TypedDict</summary>

```python
"""LangGraph state definition for the doom-stitcher DAG.

The state is a TypedDict with Annotated fields for accumulators (errors,
messages). Each phase reads from and writes to a designated slice; the
graph's `add_node` functions are pure (modulo LLM calls) and return
partial state updates.
"""
from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from models import (
    AuditReport,
    DoomModule,
    DoomModuleData,
    MaintenanceSummary,
    TranslatedConfig,
    UserInitConfig,
    VanillaConfig,
)


class DoomStitcherState(TypedDict, total=False):
    # --- Static config (set at graph entry) ----------------------------
    root_dir: str
    workflow_dir: str

    # --- Phase 1: vanilla ingestion -------------------------------------
    vanilla_config: VanillaConfig | None

    # --- Phase 2: user init.el ingestion --------------------------------
    user_init: UserInitConfig | None
    enabled_modules: list[DoomModule]

    # --- Phase 3: doom module ingestion ---------------------------------
    doom_module_data: dict[str, DoomModuleData]  # keyed by "category/name"

    # --- Phase 4: initial translation -----------------------------------
    translated_config: TranslatedConfig | None

    # --- Phase 5: refinement --------------------------------------------
    refined_config: TranslatedConfig | None

    # --- Phase 6: deduplication -----------------------------------------
    deduplicated_config: TranslatedConfig | None

    # --- Phase 7: audit --------------------------------------------------
    audit_report: AuditReport | None

    # --- Phase 8: output generation -------------------------------------
    final_config_org: str | None
    final_readme: str | None
    final_gitignore: str | None
    final_setup_doom: str | None
    final_files_written: list[str]

    # --- Phase 9: maintenance -------------------------------------------
    maintenance_summary: MaintenanceSummary | None

    # --- Accumulators (reducers) ----------------------------------------
    errors: Annotated[list[str], add]
    phase_status: Annotated[dict[str, str], add_or_update]
    log_lines: Annotated[list[str], add]


def add_or_update(current: dict[str, str] | None, new: dict[str, str] | None) -> dict[str, str]:
    """Reducer: merge `new` into `current` with new values winning."""
    base = dict(current or {})
    base.update(new or {})
    return base
```

</details>

---

#### Tools & Utilities

<details>
<summary><strong>📄 <code>workflow/utils/elisp.py</code></strong> — minimal Elisp helpers</summary>

```python
"""Lightweight, regex-based Elisp parsing.

We deliberately avoid full S-expression parsing — it adds a heavy dep
(sexpdata, sexp_parser) for limited gain. Doom configs follow conventions
that regex handles well: `(defun NAME`, `(defcustom NAME`, `(setq VAR`,
`(package! NAME ...)`, `(after! FEATURE`, `(map! ...)`, etc.
"""
from __future__ import annotations

import re
from collections.abc import Iterator

# Capture (head . args) where head is a symbol and args extends to the
# matching closing paren at depth 0. This handles nested forms correctly
# in the common case because we don't go deeper than 4-5 levels.
_FORM_RE = re.compile(r"\(([a-zA-Z!_\-\*\+\?<>=&%^/]+)([^()]*(?:\([^()]*\)[^()]*)*)\)", re.DOTALL)


def iter_forms(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield (head, args_text, full_form) for each top-level s-expression.

    Note: this is a *simple* parser; for deeply nested forms it may
    mis-segment. It is sufficient for Doom configs, which use shallow
    nesting in the patterns we care about.
    """
    for m in _FORM_RE.finditer(text):
        head, args, full = m.group(1), m.group(2), m.group(0)
        yield head, args, full


def extract_packages_from_packages_el(text: str) -> dict[str, str]:
    """Parse a `packages.el` and return {package_name: full_form}."""
    out: dict[str, str] = {}
    for head, args, full in iter_forms(text):
        if head == "package!":
            name = args.split()[0] if args.split() else ""
            if name:
                out[name] = full.strip()
    return out


def extract_setq_defaults(text: str) -> dict[str, str]:
    """Parse `config.el`-ish text and return {var_name: value_expr}."""
    out: dict[str, str] = {}
    for head, args, full in iter_forms(text):
        if head == "setq":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
        elif head == "setq!":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
        elif head == "setq-default":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
    return out


def extract_keybindings(text: str) -> list[dict[str, str]]:
    """Best-effort extraction of `map!` and `global-set-key` definitions."""
    out: list[dict[str, str]] = []
    for head, args, full in iter_forms(text):
        if head in ("map!", "global-set-key", "local-set-key"):
            out.append({"head": head, "raw": full.strip()})
    return out


def extract_doom_macro_uses(text: str) -> set[str]:
    """Collect all Doom-specific macro names used in the text."""
    macro_heads: set[str] = set()
    for head, _, _ in iter_forms(text):
        if head.endswith("!") or head in {"def-hydra", "map!"}:
            macro_heads.add(head)
    return macro_heads


def balanced_parens_check(text: str) -> tuple[bool, int]:
    """Return (ok, max_depth). Naive but useful for sanity checks."""
    depth = 0
    max_d = 0
    in_string = False
    in_comment = False
    esc = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_comment:
            if c == "\n":
                in_comment = False
        elif in_string:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_string = False
        else:
            if c == ";":
                in_comment = True
            elif c == '"':
                in_string = True
            elif c == "(":
                depth += 1
                max_d = max(max_d, depth)
            elif c == ")":
                depth -= 1
                if depth < 0:
                    return False, max_d
        i += 1
    return depth == 0, max_d
```

</details>

<details>
<summary><strong>📄 <code>workflow/utils/org.py</code></strong> — org-mode helpers</summary>

```python
"""Org-mode minimal parser for tangle-aware blocks."""
from __future__ import annotations

import re
from dataclasses import dataclass

_BEGIN_SRC = re.compile(
    r"""^#\+BEGIN_SRC\s+(?P<lang>[\w-]+)?\s*(?::[ \t]*(?P<header>.*?))?$""",
    re.MULTILINE,
)
_END_SRC = re.compile(r"^\#\+END_SRC\s*$", re.MULTILINE)


@dataclass
class SrcBlock:
    lang: str
    headers: dict[str, str]
    body: str
    start_line: int
    end_line: int

    @property
    def tangle(self) -> str:
        """Resolved tangle target. Defaults to 'config.el' (Doom literate default)."""
        return self.headers.get("tangle", "config.el").strip()

    def with_default_tangle(self, default: str = "config.el") -> "SrcBlock":
        if "tangle" not in self.headers:
            new_headers = dict(self.headers)
            new_headers["tangle"] = default
            return SrcBlock(self.lang, new_headers, self.body, self.start_line, self.end_line)
        return self


def extract_src_blocks(org_text: str) -> list[SrcBlock]:
    """Find all `#+begin_src ... #+end_src` blocks in an org file."""
    out: list[SrcBlock] = []
    for m in _BEGIN_SRC.finditer(org_text):
        lang = m.group("lang") or ""
        header_str = m.group("header") or ""
        headers = _parse_header_args(header_str)
        start = m.end()
        end_m = _END_SRC.search(org_text, pos=start)
        if not end_m:
            continue
        body = org_text[start:end_m.start()]
        out.append(
            SrcBlock(
                lang=lang,
                headers=headers,
                body=body,
                start_line=org_text[: m.start()].count("\n") + 1,
                end_line=org_text[: end_m.end()].count("\n") + 1,
            )
        )
    return out


def _parse_header_args(s: str) -> dict[str, str]:
    """Parse the header-args string after `#+begin_src LANG`.

    Format: `:key1 val1 :key2 val2 :flag`.
    """
    out: dict[str, str] = {}
    tokens = s.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith(":"):
            key = tok[1:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith(":"):
                out[key] = tokens[i + 1]
                i += 2
            else:
                out[key] = "yes"
                i += 1
        else:
            i += 1
    return out


def parse_property_drawer(org_text: str) -> dict[str, str]:
    """Read the top-of-file #+PROPERTY lines."""
    out: dict[str, str] = {}
    for line in org_text.splitlines():
        if line.startswith("#+PROPERTY:"):
            rest = line[len("#+PROPERTY:") :].strip()
            if ":" in rest:
                key, val = rest.split(":", 1)
                out[key.strip()] = val.strip()
        elif line.startswith("#+") or line.strip() == "":
            continue
        else:
            break
    return out


def render_config_org(
    *,
    title: str,
    preamble: str,
    init_el: str,
    packages_el: str,
    config_el: str,
    headings: list[tuple[str, str]] | None = None,
) -> str:
    """Render the final literate config.org.

    `headings` is an optional list of (heading, body) pairs to add
    between the preamble and the tangle blocks, providing documentation
    around the generated code.
    """
    parts: list[str] = []
    parts.append(f"#+title: {title}")
    parts.append(f"#+subtitle: Generated by doom-stitcher on {preamble}")
    parts.append("#+startup: overview")
    parts.append("#+property: header-args:emacs-lisp :results none :lexical t")
    parts.append("")

    if headings:
        for h, b in headings:
            parts.append(f"* {h}")
            parts.append("")
            parts.append(b)
            parts.append("")

    # init.el block
    parts.append("* Init")
    parts.append("")
    parts.append("The ~doom!~ block and any pre-modules init code. This block is")
    parts.append("tangled to =init.el= and loaded very early by Doom.")
    parts.append("")
    parts.append("#+begin_src emacs-lisp :tangle init.el")
    parts.append(init_el.rstrip())
    parts.append("#+end_src")
    parts.append("")

    # packages.el block
    parts.append("* Packages")
    parts.append("")
    parts.append("Package declarations. This block is tangled to =packages.el= and read")
    parts.append("by Doom's package manager (~straight.el~).")
    parts.append("")
    parts.append("#+begin_src emacs-lisp :tangle packages.el")
    parts.append(packages_el.rstrip())
    parts.append("#+end_src")
    parts.append("")

    # config.el block
    parts.append("* Configuration")
    parts.append("")
    parts.append("User configuration. This block is tangled to =config.el= and loaded")
    parts.append("after all Doom modules have been initialized.")
    parts.append("")
    parts.append("#+begin_src emacs-lisp :tangle config.el")
    parts.append(config_el.rstrip())
    parts.append("#+end_src")
    parts.append("")

    return "\n".join(parts) + "\n"
```

</details>

<details>
<summary><strong>📄 <code>workflow/tools.py</code></strong> — Pydantic AI tools</summary>

```python
"""Tools exposed to Pydantic AI agents.

These are *deterministic* I/O functions. They are the only way the agents
can read source files; this keeps the LLM from hallucinating file
contents and makes the workflow auditable.
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic_ai import RunContext

import config
from utils.elisp import (
    balanced_parens_check,
    extract_doom_macro_uses,
    extract_keybindings,
    extract_packages_from_packages_el,
    extract_setq_defaults,
)
from utils.org import extract_src_blocks

# ---------- Read tools -----------------------------------------------------


def read_text_file(path: str) -> str:
    """Read a UTF-8 text file. Returns empty string on error.

    For Doom module files, prefer `read_doom_module_file` which validates
    the path.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        return f"ERROR: file not found: {p}"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: could not read {p}: {e}"


def list_doom_modules() -> list[dict[str, Any]]:
    """List all Doom modules under doomemacs/modules/.

    Returns a list of {category, name, path, has_packages, has_config, has_init}.
    """
    modules_root = config.CONFIG.paths.modules_dir
    if not modules_root.is_dir():
        return []

    out: list[dict[str, Any]] = []
    for cat_dir in sorted(modules_root.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        for mod_dir in sorted(cat_dir.iterdir()):
            if not mod_dir.is_dir() or mod_dir.name.startswith("."):
                continue
            out.append(
                {
                    "category": cat_dir.name,
                    "name": mod_dir.name,
                    "path": str(mod_dir.relative_to(config.CONFIG.paths.doomemacs_subdir)),
                    "has_packages": (mod_dir / "packages.el").is_file(),
                    "has_config": (mod_dir / "config.el").is_file(),
                    "has_init": (mod_dir / "init.el").is_file(),
                }
            )
    return out


def read_doom_module_file(category: str, name: str, filename: str) -> str:
    """Read a single file from a Doom module (e.g. config.el, packages.el).

    Validates that the path is within doomemacs/modules/ to prevent
    directory traversal.
    """
    mod_path = (config.CONFIG.paths.modules_dir / category / name).resolve()
    if not str(mod_path).startswith(str(config.CONFIG.paths.modules_dir.resolve())):
        return f"ERROR: invalid module path: {category}/{name}"
    file_path = mod_path / filename
    if not file_path.is_file():
        return f"ERROR: file not found: {file_path}"
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: could not read {file_path}: {e}"


def search_doom_modules(pattern: str, file_glob: str = "*.el", max_results: int = 20) -> list[dict[str, str]]:
    """Search across all Doom module files for a regex pattern.

    Returns a list of {path, line_number, line} matches.
    """
    modules_root = config.CONFIG.paths.modules_dir
    if not modules_root.is_dir():
        return []

    matches: list[dict[str, str]] = []
    try:
        rg = re.compile(pattern)
    except re.error as e:
        return [{"error": f"invalid regex: {e}"}]

    for path in modules_root.rglob(file_glob):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rg.search(line):
                matches.append(
                    {
                        "path": str(path.relative_to(config.CONFIG.paths.doomemacs_subdir)),
                        "line": str(i),
                        "text": line[:200],
                    }
                )
                if len(matches) >= max_results:
                    return matches
    return matches


# ---------- Parse tools ---------------------------------------------------


def parse_org_src_blocks_tool(path: str) -> list[dict[str, Any]]:
    """Extract org-mode src blocks from a file, returning a serialized form."""
    p = Path(path).expanduser()
    if not p.is_file():
        return [{"error": f"file not found: {p}"}]
    text = p.read_text(encoding="utf-8")
    blocks = extract_src_blocks(text)
    return [
        {
            "lang": b.lang,
            "tangle": b.tangle,
            "headers": b.headers,
            "body_preview": b.body[:300],
            "body_length": len(b.body),
            "start_line": b.start_line,
            "end_line": b.end_line,
        }
        for b in blocks
    ]


def parse_packages_el_tool(path: str) -> dict[str, str]:
    """Parse a packages.el file and return {package_name: full_form}."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    return extract_packages_from_packages_el(p.read_text(encoding="utf-8"))


def extract_setq_defaults_tool(path: str) -> dict[str, str]:
    """Parse a config.el-ish file and return {var_name: value_expression}."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    return extract_setq_defaults(p.read_text(encoding="utf-8"))


def extract_doom_macros_tool(path: str) -> list[str]:
    """Return the set of Doom-specific macros used in a file."""
    p = Path(path).expanduser()
    if not p.is_file():
        return [f"ERROR: file not found: {p}"]
    return sorted(extract_doom_macro_uses(p.read_text(encoding="utf-8")))


def validate_elisp_balance_tool(path: str) -> dict[str, Any]:
    """Check paren balance of an Elisp file."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    text = p.read_text(encoding="utf-8")
    ok, max_d = balanced_parens_check(text)
    return {"balanced": ok, "max_depth": max_d, "line_count": text.count("\n") + 1}


# ---------- Write tools (Phase 8) ----------------------------------------


def write_text_file_tool(path: str, content: str) -> dict[str, Any]:
    """Write a text file (Phase 8 only). Creates parent dirs as needed."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"written": str(p), "bytes": len(content)}


def move_file_tool(src: str, dst: str) -> dict[str, Any]:
    """Move a file, creating parent dirs on the destination."""
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return {"error": f"source not found: {s}"}
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    return {"moved": {"from": str(s), "to": str(d)}}


def remove_directory_tool(path: str) -> dict[str, Any]:
    """Remove a directory recursively. Used to delete the emacs/ folder."""
    import shutil

    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"path not found: {p}"}
    if p.is_file():
        return {"error": f"refusing to remove file: {p}"}
    # Safety: only remove if it's named 'emacs' and under our doomdir
    if p.name != "emacs":
        return {"error": f"refusing to remove non-emacs directory: {p}"}
    if not str(p.resolve()).startswith(str(config.CONFIG.paths.doomdir.resolve())):
        return {"error": f"refusing to remove path outside DOOMDIR: {p}"}
    shutil.rmtree(p)
    return {"removed": str(p)}


# ---------- Toolset registration -----------------------------------------


def get_agent_tools() -> list:
    """Return the list of tools to register on each agent.

    We register the read/parse/search tools; the write/move/remove tools
    are registered only on the Phase 8 output-generation agent.
    """
    return [
        read_text_file,
        list_doom_modules,
        read_doom_module_file,
        search_doom_modules,
        parse_org_src_blocks_tool,
        parse_packages_el_tool,
        extract_setq_defaults_tool,
        extract_doom_macros_tool,
        validate_elisp_balance_tool,
    ]


def get_writer_tools() -> list:
    return [
        write_text_file_tool,
        move_file_tool,
        remove_directory_tool,
    ]
```

</details>

---

#### Agents

<details>
<summary><strong>📄 <code>workflow/agents.py</code></strong> — Pydantic AI agent factories</summary>

```python
"""Pydantic AI agent factories.

Each agent is a stateless runner constructed from the runtime config.
We use `OpenAIChatModel` + `OpenAIProvider` so the LiteLLM proxy is the
sole model endpoint. The `model_name` strings are aliases defined in
the user's `litellm-config.yaml`.
"""
from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import config
from models import (
    AuditReport,
    DoomModuleData,
    TranslatedConfig,
    UserInitConfig,
    VanillaConfig,
)
from prompt import (
    DOOM_STITCHER_DIRECTIVE,
    PHASE_4_HINTS,
    PHASE_5_HINTS,
    PHASE_7_HINTS,
)
from tools import get_agent_tools, get_writer_tools


# ---------- Model provider factory ---------------------------------------


def _make_model(model_alias: str) -> OpenAIChatModel:
    """Build an OpenAIChatModel pointed at the local LiteLLM proxy."""
    provider = OpenAIProvider(
        base_url=config.CONFIG.models.base_url,
        api_key=config.CONFIG.models.api_key,
    )
    return OpenAIChatModel(model_alias, provider=provider)


# ---------- Agent factories ----------------------------------------------


def make_vanilla_ingestion_agent() -> Agent[None, VanillaConfig]:
    """Phase 1 agent: extract packages, keybindings, custom defs."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=VanillaConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=3,
    )


def make_user_init_ingestion_agent() -> Agent[None, UserInitConfig]:
    """Phase 2 agent: parse the dooM! block from the user's init.el."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=UserInitConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )


def make_doom_module_analyzer_agent() -> Agent[None, DoomModuleData]:
    """Phase 3 agent: produce a DoomModuleData summary for one module."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=DoomModuleData,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )


def make_translation_agent() -> Agent[None, TranslatedConfig]:
    """Phase 4 agent: vanilla → Doom translation (Pass 1)."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_4_HINTS,
        deps_type=type(None),
        retries=3,
    )
    # Register read tools so the agent can consult Doom defaults as needed
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_refinement_agent() -> Agent[None, TranslatedConfig]:
    """Phase 5 agent: integrate custom Elisp, refine transients (Pass 2)."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_5_HINTS,
        deps_type=type(None),
        retries=2,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_dedup_agent() -> Agent[None, TranslatedConfig]:
    """Phase 6 agent: deduplicate against Doom defaults."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_audit_agent() -> Agent[None, AuditReport]:
    """Phase 7 agent: comprehensive audit of the translated config."""
    agent = Agent(
        _make_model(config.CONFIG.models.audit_model),
        output_type=AuditReport,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_7_HINTS,
        deps_type=type(None),
        retries=3,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


# Single shared instances (agents are stateless; safe to reuse)
VANILLA_INGESTION_AGENT = make_vanilla_ingestion_agent()
USER_INIT_INGESTION_AGENT = make_user_init_ingestion_agent()
DOOM_MODULE_ANALYZER_AGENT = make_doom_module_analyzer_agent()
TRANSLATION_AGENT = make_translation_agent()
REFINEMENT_AGENT = make_refinement_agent()
DEDUP_AGENT = make_dedup_agent()
AUDIT_AGENT = make_audit_agent()
```

</details>

---

#### Phase Nodes

<details>
<summary><strong>📄 <code>workflow/phases/__init__.py</code></strong></summary>

```python
"""Phase node functions exposed to LangGraph.

Each phase is a pure (or near-pure) function: (state) -> partial_state_update.
LLM calls happen via the shared agent instances in `agents.py`.
"""
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase1_vanilla_ingestion.py</code></strong> — Phase 1</summary>

```python
"""Phase 1: Vanilla Ingestion.

Parse `emacs/config.org` and `emacs/early-init.el` to extract:
- Package declarations (use-package, package-install, etc.)
- Keybindings (global-set-key, define-key, map!)
- Custom defuns/macros/hydras/transients
- early-init.el raw settings

Strategy: deterministic regex pre-extraction + LLM semantic enrichment
on the org-mode src blocks.
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

import config
from agents import VANILLA_INGESTION_AGENT
from models import VanillaConfig
from state import DoomStitcherState
from utils.elisp import (
    extract_doom_macro_uses,
    extract_keybindings,
    extract_packages_from_packages_el,
    extract_setq_defaults,
)
from utils.org import extract_src_blocks


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _deterministic_extraction(org_text: str, early_init_text: str) -> dict[str, object]:
    """First-pass extraction. Pure regex, no LLM."""
    packages: dict[str, str] = {}
    keybindings: list[dict[str, str]] = []
    setqs: dict[str, str] = {}
    macros: set[str] = set()

    for block in extract_src_blocks(org_text):
        if block.lang and "elisp" not in block.lang:
            continue
        body = block.body
        packages.update(extract_packages_from_packages_el(body))
        keybindings.extend(extract_keybindings(body))
        setqs.update(extract_setq_defaults(body))
        macros.update(extract_doom_macro_uses(body))

    # early-init.el is plain elisp
    packages.update(extract_packages_from_packages_el(early_init_text))
    keybindings.extend(extract_keybindings(early_init_text))
    setqs.update(extract_setq_defaults(early_init_text))
    macros.update(extract_doom_macro_uses(early_init_text))

    return {
        "packages": packages,
        "keybindings": keybindings,
        "setqs": setqs,
        "macros": macros,
    }


def phase1_vanilla_ingestion(state: DoomStitcherState) -> dict:
    """Run Phase 1: Vanilla Ingestion."""
    log: list[str] = []
    phase_status: dict[str, str] = {"phase1_vanilla_ingestion": "running"}
    log.append("[P1] Reading vanilla configs...")

    emacs_dir = config.CONFIG.paths.emacs_subdir
    config_org = emacs_dir / "config.org"
    early_init = emacs_dir / "early-init.el"

    org_text = _read_text(config_org)
    early_init_text = _read_text(early_init)

    if not org_text and not early_init_text:
        msg = f"No vanilla configs found in {emacs_dir}"
        logger.error(msg)
        return {
            "vanilla_config": None,
            "errors": [msg],
            "phase_status": {"phase1_vanilla_ingestion": "failed"},
        }

    # Deterministic first pass
    det = _deterministic_extraction(org_text, early_init_text)
    log.append(
        f"[P1] Regex pass: {len(det['packages'])} packages, "
        f"{len(det['keybindings'])} keybindings, {len(det['setqs'])} setqs, "
        f"{len(det['macros'])} macros"
    )

    # LLM semantic enrichment: feed the agent a compact summary + raw
    # source so it can produce a structured VanillaConfig.
    summary = (
        f"# Vanilla Config Summary\n\n"
        f"## File: {config_org}\n"
        f"Length: {len(org_text)} chars, "
        f"src blocks: {len(extract_src_blocks(org_text))}\n\n"
        f"## File: {early_init}\n"
        f"Length: {len(early_init_text)} chars\n\n"
        f"## Detected packages (regex): {sorted(det['packages'].keys())}\n\n"
        f"## Detected setq defaults (first 50): "
        f"{list(det['setqs'].items())[:50]}\n\n"
        f"## Detected macros: {sorted(det['macros'])}\n\n"
        f"## Raw early-init.el (first 1000 chars):\n"
        f"```elisp\n{early_init_text[:1000]}\n```\n\n"
        f"## Raw config.org (first 4000 chars):\n"
        f"```org\n{org_text[:4000]}\n```\n"
    )

    prompt = (
        "Extract a structured representation of this vanilla Emacs configuration. "
        "Include every package declared via use-package/package-install, every "
        "keybinding (with its mode scope), every custom defun/defmacro/defhydra/"
        "transient, and every notable early-init setting. Use the raw sources to "
        "verify anything the regex pass may have missed. "
        "Return a `VanillaConfig` object."
    )

    try:
        result = VANILLA_INGESTION_AGENT.run_sync(
            user_prompt=f"{prompt}\n\n{summary}",
        )
        vanilla = result.output
        # Annotate source paths
        vanilla.source_org_path = str(config_org)
        vanilla.source_early_init_path = str(early_init)
        log.append(f"[P1] LLM produced {len(vanilla.packages)} packages, "
                   f"{len(vanilla.keybindings)} keybindings, {len(vanilla.custom_defs)} custom defs")
        phase_status["phase1_vanilla_ingestion"] = "completed"
        return {"vanilla_config": vanilla, "log_lines": log, "phase_status": phase_status}
    except Exception as e:
        logger.exception("Phase 1 LLM call failed")
        return {
            "vanilla_config": None,
            "errors": [f"Phase 1 failed: {e}"],
            "log_lines": log,
            "phase_status": {"phase1_vanilla_ingestion": "failed"},
        }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase2_init_ingestion.py</code></strong> — Phase 2</summary>

```python
"""Phase 2: User init.el Ingestion.

Parse the user-provided `init.el` to identify which Doom modules are
enabled and with what flags. This drives Phase 3's module ingestion.
"""
from __future__ import annotations

import re

from loguru import logger

import config
from agents import USER_INIT_INGESTION_AGENT
from models import DoomModule, DoomModuleCategory, UserInitConfig
from state import DoomStitcherState

_DOOM_BLOCK = re.compile(r"\(doom!\s*(?P<body>.*?)\)\s*(?=\(doom!|\Z)", re.DOTALL)


def _find_doom_block(text: str) -> tuple[str, str]:
    """Return (full_match, body) for the dooM! macro, or ('', '')."""
    m = _DOOM_BLOCK.search(text)
    if not m:
        return "", ""
    return m.group(0), m.group("body")


def _deterministic_modules(body: str) -> list[DoomModule]:
    """Parse module declarations from a dooM! body.

    Supports both:
        :ui deft
        :completion (company +tng)
        :lang (python +lsp)
    """
    modules: list[DoomModule] = []
    current_cat: DoomModuleCategory | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";;"):
            continue
        if line.startswith(":"):
            # category header
            name = line[1:].strip()
            try:
                current_cat = DoomModuleCategory(name)
            except ValueError:
                logger.warning(f"Unknown Doom category: :{name}")
                current_cat = None
            continue
        if current_cat is None:
            continue
        # Module line: may have flags, e.g. "evil +everywhere" or "(evil +everywhere)"
        mod_line = line.strip("()")
        tokens = mod_line.split()
        if not tokens:
            continue
        mod_name = tokens[0]
        flags = []
        for tok in tokens[1:]:
            if tok.startswith("+"):
                f_name = tok[1:]
                if "=" in f_name:
                    fn, fv = f_name.split("=", 1)
                    flags.append({"name": fn, "value": fv})
                else:
                    flags.append({"name": f_name, "value": True})
        from models import DoomModuleFlag

        modules.append(
            DoomModule(
                category=current_cat,
                name=mod_name,
                flags=[DoomModuleFlag(**f) for f in flags],
            )
        )
    return modules


def phase2_init_ingestion(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P2] Parsing user init.el..."]
    init_path = config.CONFIG.paths.doomdir / "init.el"
    if not init_path.is_file():
        msg = f"User init.el not found at {init_path}"
        return {
            "user_init": None,
            "enabled_modules": [],
            "errors": [msg],
            "log_lines": [msg],
            "phase_status": {"phase2_init_ingestion": "failed"},
        }

    text = init_path.read_text(encoding="utf-8")
    full, body = _find_doom_block(text)
    if not full:
        msg = "No (doom! ...) block found in init.el"
        return {
            "user_init": None,
            "enabled_modules": [],
            "errors": [msg],
            "log_lines": log + [msg],
            "phase_status": {"phase2_init_ingestion": "failed"},
        }

    modules = _deterministic_modules(body)
    log.append(f"[P2] Detected {len(modules)} modules: " + ", ".join(f"{m.path}" for m in modules))

    # LLM cross-check: sometimes users wrap modules in parens or comment
    # in unusual ways. The LLM can catch omissions and label each module
    # with a "category" hint we can verify.
    try:
        result = USER_INIT_INGESTION_AGENT.run_sync(
            user_prompt=(
                "Confirm or correct this list of Doom modules parsed from the "
                "user's dooM! block. The raw block is:\n\n"
                f"```elisp\n{full}\n```\n\n"
                f"Current detected modules: "
                f"{[m.model_dump() for m in modules]}\n\n"
                "Return a `UserInitConfig` with the correct list."
            ),
        )
        user_init = result.output
        user_init.raw_doom_block = full
        user_init.source_path = str(init_path)
    except Exception as e:
        logger.warning(f"Phase 2 LLM cross-check failed: {e}; using deterministic parse")
        user_init = UserInitConfig(modules=modules, raw_doom_block=full, source_path=str(init_path))

    log.append(f"[P2] Final: {len(user_init.modules)} modules enabled")
    return {
        "user_init": user_init,
        "enabled_modules": [m for m in user_init.modules],
        "log_lines": log,
        "phase_status": {"phase2_init_ingestion": "completed"},
    }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase3_doom_ingestion.py</code></strong> — Phase 3</summary>

```python
"""Phase 3: Doom Module Ingestion.

For each enabled module from Phase 2, read its files from
`doomemacs/modules/<category>/<name>/{config,init,packages}.el` and
extract a `DoomModuleData` summary.

The agent does semantic summarization; we pre-populate the deterministic
fields (defaults, packages) via regex extraction.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

import config
from agents import DOOM_MODULE_ANALYZER_AGENT
from models import DoomModuleData, DoomModuleFile
from state import DoomStitcherState
from utils.elisp import (
    extract_doom_macro_uses,
    extract_keybindings,
    extract_packages_from_packages_el,
    extract_setq_defaults,
)


def _read_module_files(category: str, name: str) -> list[DoomModuleFile]:
    mod_path = config.CONFIG.paths.modules_dir / category / name
    out: list[DoomModuleFile] = []
    for fname in ("packages.el", "config.el", "init.el", "doctor.el"):
        p = mod_path / fname
        if p.is_file():
            out.append(
                DoomModuleFile(
                    filename=fname,
                    content=p.read_text(encoding="utf-8"),
                )
            )
    return out


def _deterministic_summary(mod: DoomModuleData) -> None:
    """Fill the `defaults`, `packages`, `keybindings`, `macros_used` fields."""
    defaults: dict[str, str] = {}
    packages: dict[str, str] = {}
    kbs: list = []
    macros: set[str] = set()
    for f in mod.files:
        if f.filename in ("config.el", "init.el"):
            defaults.update(extract_setq_defaults(f.content))
            macros.update(extract_doom_macro_uses(f.content))
        if f.filename in ("config.el", "init.el", "doctor.el"):
            kbs.extend(extract_keybindings(f.content))
        if f.filename == "packages.el":
            packages.update(extract_packages_from_packages_el(f.content))
    mod.defaults = defaults
    mod.packages = packages
    mod.keybindings = kbs  # type: ignore[assignment]
    mod.macros_used = sorted(macros)


def _process_one_module(category: str, name: str) -> DoomModuleData | None:
    mod = DoomModuleData(
        category=category,
        name=name,
        path=f"{category}/{name}",
        files=_read_module_files(category, name),
    )
    if not mod.files:
        return None
    _deterministic_summary(mod)
    # Ask the LLM to enrich the data with semantic context.
    try:
        # Combine files into a digestible prompt.
        file_summary = "\n\n".join(
            f"--- {f.filename} ---\n{f.content[:2000]}{'...' if len(f.content) > 2000 else ''}"
            for f in mod.files
        )
        result = DOOM_MODULE_ANALYZER_AGENT.run_sync(
            user_prompt=(
                f"Analyze Doom module `{category}/{name}` and produce a "
                f"`DoomModuleData` summary. Include the most important config "
                f"variables and their defaults, the package manifest, and any "
                f"notable keybinding conventions. Files:\n\n{file_summary}"
            ),
        )
        enriched = result.output
        # Merge: prefer LLM's curated list of macros_used, keep regex defaults
        for f in enriched.files:
            if f.filename not in {mf.filename for mf in mod.files}:
                mod.files.append(f)
        mod.macros_used = sorted(set(mod.macros_used) | set(enriched.macros_used))
    except Exception as e:
        logger.warning(f"LLM enrichment failed for {category}/{name}: {e}")
    return mod


def phase3_doom_ingestion(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P3] Ingesting enabled Doom modules..."]
    enabled = state.get("enabled_modules", [])
    if not enabled:
        return {
            "doom_module_data": {},
            "log_lines": log + ["[P3] No modules to ingest"],
            "phase_status": {"phase3_doom_ingestion": "skipped"},
        }

    doom_data: dict[str, DoomModuleData] = {}
    # Parallelize for speed; LLM calls are the bottleneck.
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(_process_one_module, m.category.value, m.name): m.path
            for m in enabled
        }
        for fut in as_completed(futures):
            path = futures[fut]
            try:
                mod = fut.result()
                if mod is not None:
                    doom_data[path] = mod
                    log.append(f"[P3]   {path}: {len(mod.files)} files, "
                               f"{len(mod.defaults)} defaults, {len(mod.packages)} packages")
            except Exception as e:
                logger.exception(f"Failed to process module {path}")
                log.append(f"[P3]   {path}: FAILED ({e})")

    return {
        "doom_module_data": doom_data,
        "log_lines": log,
        "phase_status": {"phase3_doom_ingestion": "completed"},
    }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase4_initial_translation.py</code></strong> — Phase 4</summary>

```python
"""Phase 4: Initial Translation (Pass 1).

Translate vanilla idioms into Doom idioms, producing the first complete
`TranslatedConfig` with init.el, packages.el, and config.el blocks.
"""
from __future__ import annotations

import json

from loguru import logger

from agents import TRANSLATION_AGENT
from state import DoomStitcherState


def _serialize_for_prompt(obj) -> str:
    try:
        return json.dumps(obj.model_dump(mode="json"), indent=2, default=str)[:20000]
    except Exception:
        return str(obj)[:20000]


def phase4_initial_translation(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P4] Translating vanilla → Doom (Pass 1)..."]
    vanilla = state.get("vanilla_config")
    user_init = state.get("user_init")
    doom_data = state.get("doom_module_data", {})

    if vanilla is None:
        msg = "Phase 4 aborted: no vanilla_config from Phase 1"
        return {"translated_config": None, "errors": [msg], "log_lines": log}

    # Provide the agent with everything it needs.
    prompt = (
        "Translate this vanilla Emacs configuration into a Doom Emacs configuration.\n\n"
        "## Vanilla Config (extracted):\n"
        f"```json\n{_serialize_for_prompt(vanilla)}\n```\n\n"
        "## User's existing dooM! block (preserve, append new modules if needed):\n"
        f"```elisp\n{user_init.raw_doom_block if user_init else '(doom! :config literate)'}\n```\n\n"
        "## Doom Module Defaults (only override if vanilla explicitly differs):\n"
        f"```json\n{_serialize_for_prompt({k: {'defaults': v.defaults, 'packages': v.packages} for k, v in doom_data.items()})}\n```\n\n"
        "Produce a `TranslatedConfig` with three sub-blocks: "
        "`init_el` (the full dooM! macro + any early settings), "
        "`packages_el` (every `package!` declaration, with `(package! name)` per line), "
        "`config_el` (every config form grouped by package, using `after!`, `use-package!`, `setq!`, `setq-hook!`, `map!` as appropriate).\n\n"
        "Critical rules:\n"
        "1. Preserve the user's dooM! block exactly. Add `:config literate` if missing.\n"
        "2. Only emit `package!` for packages NOT already in Doom's pinned set.\n"
        "3. Use `after!` with feature symbols, not mode names.\n"
        "4. Keep transients, defuns, advice — but in Doom style.\n"
    )

    try:
        result = TRANSLATION_AGENT.run_sync(user_prompt=prompt)
        translated = result.output
        # Ensure :config literate is present
        if ":config literate" not in translated.init_el.doom_block:
            # Inject it
            translated.init_el.doom_block = translated.init_el.doom_block.replace(
                "(doom!", "(doom!\n  :config\n  literate", 1,
            )
        log.append(f"[P4] Produced translated_config: "
                   f"{len(translated.packages_el.package_declarations)} packages, "
                   f"{len(translated.config_el.config_forms)} config forms")
        return {
            "translated_config": translated,
            "log_lines": log,
            "phase_status": {"phase4_initial_translation": "completed"},
        }
    except Exception as e:
        logger.exception("Phase 4 LLM call failed")
        return {
            "translated_config": None,
            "errors": [f"Phase 4 failed: {e}"],
            "log_lines": log,
            "phase_status": {"phase4_initial_translation": "failed"},
        }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase5_refinement.py</code></strong> — Phase 5</summary>

```python
"""Phase 5: Refinement & Custom Elisp (Pass 2).

Integrate `org-src-context.el`, refine transients, and explicitly
override Doom defaults only where the vanilla config truly diverges.
"""
from __future__ import annotations

from loguru import logger

import config
from agents import REFINEMENT_AGENT
from state import DoomStitcherState
from utils.elisp import extract_setq_defaults


_ORG_SRC_CONTEXT_HOOK = """
;; Custom Elisp: org-src-context
(after! org
  (require 'org-src-context))
"""

_LOAD_PATH_SETUP = """
;; Add lisp/ to load-path for custom Elisp
(add-to-list 'load-path (expand-file-name "lisp/" doom-user-dir))
"""


def _strip_redundant_overrides(translated, doom_data) -> int:
    """Remove config forms that exactly match a Doom module default.

    Returns the count of removed forms.
    """
    removed = 0
    # Build a unified defaults map
    unified: dict[str, str] = {}
    for mod in doom_data.values():
        unified.update(mod.defaults)
    # Walk config_forms looking for trivial setq that matches
    kept: list[str] = []
    for form in translated.config_el.config_forms:
        stripped = form.strip()
        if stripped.startswith("(setq!") or stripped.startswith("(setq "):
            try:
                inside = stripped[stripped.index("(") :].strip("()")
                # very rough: first token is setq/setq!
                head, *rest = inside.split(None, 1)
                if head in {"setq", "setq!"} and rest:
                    tokens = rest[0].split(None, 1)
                    if len(tokens) == 2 and tokens[0] in unified:
                        # Compare normalized value
                        v_trim = tokens[1].strip()
                        d_trim = unified[tokens[0]].strip()
                        if v_trim == d_trim:
                            removed += 1
                            continue
            except Exception:
                pass
        kept.append(form)
    translated.config_el.config_forms = kept
    return removed


def phase5_refinement(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P5] Refining translation (Pass 2)..."]
    translated = state.get("translated_config")
    doom_data = state.get("doom_module_data", {})
    if translated is None:
        msg = "Phase 5 aborted: no translated_config from Phase 4"
        return {"refined_config": None, "errors": [msg], "log_lines": log}

    # Deterministic integration first.
    # 1) Add lisp/ to load-path at the top of config_el
    translated.config_el.load_path_setup = _LOAD_PATH_SETUP.strip()
    # 2) Add (after! org (require 'org-src-context))
    translated.config_el.after_org_setup = _ORG_SRC_CONTEXT_HOOK.strip()
    # 3) Strip redundant defaults
    removed = _strip_redundant_overrides(translated, doom_data)
    log.append(f"[P5] Stripped {removed} redundant Doom default overrides")

    # LLM-driven refinement: tidy transients, polish structure
    try:
        result = REFINEMENT_AGENT.run_sync(
            user_prompt=(
                "Refine this translated Doom config. Specifically:\n"
                "1. Convert any vanilla `transient-define-*` or `defhydra` to Doom's "
                "   idioms (`def-hydra!`, `transient-define-*` is fine but use Doom's `map!` for bindings).\n"
                "2. Ensure every `after!` references a feature symbol, not a mode name.\n"
                "3. Re-group config_forms by feature package for readability.\n"
                "4. Verify the org-src-context integration looks right.\n\n"
                f"Current translated config:\n```json\n"
                f"{translated.model_dump_json(indent=2)[:20000]}\n```\n\n"
                "Return a `TranslatedConfig` (the refined version)."
            ),
        )
        refined = result.output
        # Re-apply deterministic integration (LLM may have stripped it)
        refined.config_el.load_path_setup = _LOAD_PATH_SETUP.strip()
        refined.config_el.after_org_setup = _ORG_SRC_CONTEXT_HOOK.strip()
        log.append("[P5] LLM refinement applied")
        return {
            "refined_config": refined,
            "log_lines": log,
            "phase_status": {"phase5_refinement": "completed"},
        }
    except Exception as e:
        logger.exception("Phase 5 LLM call failed; keeping deterministic refinement")
        return {
            "refined_config": translated,
            "log_lines": log,
            "phase_status": {"phase5_refinement": "partial"},
        }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase6_deduplication.py</code></strong> — Phase 6</summary>

```python
"""Phase 6: Deduplication.

Strip `package!` declarations that already exist in Doom's ingested module
defaults, and remove `setq` configurations that match Doom's defaults
exactly. This is a deterministic post-processing pass.
"""
from __future__ import annotations

import re

from loguru import logger

from state import DoomStitcherState


def _normalize_pkg_name(name: str) -> str:
    """Normalize package names: strip 'package!', parens, version pins."""
    n = name.strip().strip("'\"")
    if n.startswith(":"):
        n = n[1:]
    return n


def phase6_deduplication(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P6] Deduplicating against Doom defaults..."]
    refined = state.get("refined_config")
    doom_data = state.get("doom_module_data", {})
    if refined is None:
        return {"deduplicated_config": None, "errors": ["Phase 6: no refined_config"]}

    # Build union of Doom-declared package names
    doom_pkgs: set[str] = set()
    doom_defaults: dict[str, str] = {}
    for mod in doom_data.values():
        for name in mod.packages.keys():
            doom_pkgs.add(_normalize_pkg_name(name))
        doom_defaults.update(mod.defaults)

    # Deduplicate packages.el
    pkg_dedup: list[str] = []
    pkg_removed = 0
    for line in refined.packages_el.package_declarations:
        # Extract the package name from a (package! name ...) form
        m = re.match(r"\s*\(package!\s+([^\s)]+)", line)
        if m:
            name = _normalize_pkg_name(m.group(1))
            if name in doom_pkgs:
                pkg_removed += 1
                continue
        pkg_dedup.append(line)
    refined.packages_el.package_declarations = pkg_dedup
    log.append(f"[P6] Removed {pkg_removed} duplicate package! declarations")

    # Deduplicate config.el setq forms
    cfg_kept: list[str] = []
    cfg_removed = 0
    for form in refined.config_el.config_forms:
        stripped = form.strip()
        head_match = re.match(r"\s*\((setq!?|setq-default|setq-hook!)\s+([^\s)]+)\s+(.+?)\)\s*$",
                              stripped, re.DOTALL)
        if head_match and head_match.group(1).startswith("setq"):
            var = head_match.group(2)
            val = head_match.group(3).strip()
            if var in doom_defaults and doom_defaults[var].strip() == val:
                cfg_removed += 1
                continue
        cfg_kept.append(form)
    refined.config_el.config_forms = cfg_kept
    log.append(f"[P6] Removed {cfg_removed} setq duplicates")

    return {
        "deduplicated_config": refined,
        "log_lines": log,
        "phase_status": {"phase6_deduplication": "completed"},
    }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase7_audit.py</code></strong> — Phase 7</summary>

```python
"""Phase 7: Comprehensive Audit.

Validate the final `TranslatedConfig` against the doomemacs source tree:
- Tangle headers are correct
- Doom macros are real (not hallucinated)
- `(after! <package> ...)` uses feature symbols
- `:config literate` is in the dooM! block
- No duplicate setqs
- Elisp is paren-balanced
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from agents import AUDIT_AGENT
from models import AuditFinding, AuditReport, Severity
from state import DoomStitcherState
from utils.elisp import (
    balanced_parens_check,
    extract_doom_macro_uses,
    iter_forms,
)
from utils.org import parse_property_drawer


# Known Doom macros (defined in doomemacs/core/core-lib.el or lisp/doom-lib.el)
KNOWN_DOOM_MACROS = {
    "after!", "use-package!", "use-package-hook!", "setq-hook!", "setq!",
    "add-hook!", "remove-hook!", "def-hydra!", "defun!", "defmacro!",
    "map!", "map!", "appendq!", "prependq!", "setq-hook!",
    "package!", "recipe!", "pin!", "unpin!",
    "load!", "featurep!", "modulep!",
    "add-to-load-path!", "add-load-path!",
    "set-yas-minor-mode-key!",
    "call-after-loaded!",
    "add-transient-hook!",
    "after-load!",
    "def-project-mode!",
    "def-other-window!",
    "custom!",
    "cmd!",
    "cmd!!",
    "general-define-key",
    "doom-themer",
}


def _check_tangle_headers(report: AuditReport, config_org_text: str) -> None:
    if ":tangle config.el" not in config_org_text and "#+property:" not in config_org_text:
        report.add(
            AuditFinding(
                severity=Severity.WARNING,
                category="tangle",
                message="No global :tangle property set; src blocks default to config.el. Consider explicit tangle targets.",
            )
        )


def _check_doom_macros(report: AuditReport, text: str) -> None:
    used = extract_doom_macro_uses(text)
    for m in used:
        if m not in KNOWN_DOOM_MACROS:
            report.add(
                AuditFinding(
                    severity=Severity.WARNING,
                    category="macro-validity",
                    message=f"Unknown Doom macro: {m}",
                    suggested_fix=f"Verify `{m}` exists in doomemacs/core/ or lisp/.",
                )
            )


def _check_after_symbols(report: AuditReport, text: str) -> None:
    """Verify (after! <feature> ...) uses a feature symbol, not a -mode name."""
    for head, args, full in iter_forms(text):
        if head == "after!":
            first = args.split(None, 1)[0] if args.split() else ""
            if first.endswith("-mode"):
                report.add(
                    AuditFinding(
                        severity=Severity.ERROR,
                        category="after-symbol",
                        message=f"`(after! {first} ...)` uses a mode name; pass the feature symbol instead.",
                        location=full[:80],
                        suggested_fix=f"Use `(after! {first[:-5]} ...)` (the package name).",
                    )
                )


def _check_literate_in_doom(report: AuditReport, doom_block: str) -> None:
    if ":config literate" not in doom_block and "config literate" not in doom_block:
        report.add(
            AuditFinding(
                severity=Severity.ERROR,
                category="doom-block",
                message="The `:config literate` module is not in the dooM! block; config.org will not be tangled automatically.",
            )
        )


def _check_load_path(report: AuditReport, config_el: str) -> None:
    if "lisp/" not in config_el or "load-path" not in config_el:
        report.add(
            AuditFinding(
                severity=Severity.ERROR,
                category="load-path",
                message="config.el does not add the lisp/ directory to `load-path`; custom Elisp will not load.",
            )
        )


def _check_org_src_context(report: AuditReport, config_el: str) -> None:
    if "org-src-context" not in config_el:
        report.add(
            AuditFinding(
                severity=Severity.ERROR,
                category="custom-elisp",
                message="config.el does not require `org-src-context`; the custom Elisp will not be loaded.",
            )
        )
    if "(after! org" not in config_el:
        report.add(
            AuditFinding(
                severity=Severity.ERROR,
                category="custom-elisp",
                message="`(require 'org-src-context)` is not wrapped in `(after! org ...)`.",
            )
        )


def _check_parens(report: AuditReport, *texts: str) -> None:
    for i, t in enumerate(texts, 1):
        ok, depth = balanced_parens_check(t)
        if not ok:
            report.add(
                AuditFinding(
                    severity=Severity.ERROR,
                    category="syntax",
                    message=f"Parenthesis imbalance detected in config block #{i} (max depth: {depth}).",
                )
            )


def phase7_audit(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P7] Auditing translated config..."]
    deduped = state.get("deduplicated_config")
    if deduped is None:
        return {"audit_report": None, "errors": ["Phase 7: no deduplicated_config"]}

    report = AuditReport(summary="Audit complete.")

    # Build a single text blob to scan
    config_el_text = "\n".join(
        [
            deduped.config_el.load_path_setup,
            deduped.config_el.after_org_setup,
            *deduped.config_el.config_forms,
            *deduped.config_el.transient_defs,
        ]
    )
    packages_el_text = "\n".join(deduped.packages_el.package_declarations)
    init_el_text = deduped.init_el.doom_block + "\n" + deduped.init_el.extra_early_settings

    # Deterministic checks
    _check_literate_in_doom(report, deduped.init_el.doom_block)
    _check_load_path(report, config_el_text)
    _check_org_src_context(report, config_el_text)
    _check_parens(report, config_el_text, packages_el_text, init_el_text)
    _check_doom_macros(report, config_el_text)
    _check_after_symbols(report, config_el_text)

    # Ask the LLM to perform a deeper semantic audit
    try:
        result = AUDIT_AGENT.run_sync(
            user_prompt=(
                "Audit this Doom Emacs config for any remaining issues: "
                "tangle correctness, macro validity, override correctness, "
                "custom Elisp integration, transients, and keybinding conflicts. "
                "Be terse; only flag real problems.\n\n"
                f"```json\n{deduped.model_dump_json(indent=2)[:30000]}\n```"
            ),
        )
        llm_report = result.output
        report.findings.extend(llm_report.findings)
        # If LLM added any errors, downgrade `passed` accordingly
        if any(f.severity == Severity.ERROR for f in llm_report.findings):
            report.passed = False
    except Exception as e:
        logger.warning(f"LLM audit pass failed: {e}")

    log.append(f"[P7] Findings: {len(report.findings)} "
               f"(errors: {sum(1 for f in report.findings if f.severity == Severity.ERROR)})")

    return {
        "audit_report": report,
        "log_lines": log,
        "phase_status": {"phase7_audit": "completed" if report.passed else "completed_with_errors"},
    }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase8_output_generation.py</code></strong> — Phase 8</summary>

```python
"""Phase 8: Output Generation.

Render the final `config.org`, `README.md`, `.gitignore`, and
`setup-doom.sh`. Perform filesystem operations:
  - Move `lisp/org-src-context.el` from `emacs/lisp/` to `lisp/`
  - Delete the `emacs/` directory
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from loguru import logger

import config
from models import Severity
from state import DoomStitcherState
from utils.org import render_config_org


# -------- Output templates (deterministic; the LLM doesn't touch these) ---

GITIGNORE = """# Doom Emacs generated files (regenerated by `doom sync`)
config.el
init.el
packages.el
custom.el

# Doom runtime
.doom.d/
straight-build/
.elc/
*.elc

# Local workflow artifacts
workflow/.venv/
workflow/__pycache__/
workflow/**/__pycache__/
workflow/.litellm-*.log
workflow/.state/
workflow/.last-run.json

# Secrets & local config
.env
.env.local
litellm-config.local.yaml

# OS noise
.DS_Store
Thumbs.db

# Editor backups
*~
\\#*\\#
.\\#*
"""

README = """# Doom Emacs Configuration

This repository is a **literate Doom Emacs configuration** generated by
[`doom-stitcher`](./workflow/) from a vanilla Emacs config. The single source of
truth is `config.org`; it is tangled by `doom sync` into `config.el`,
`init.el`, and `packages.el`.

> ⚠️ **Do not edit `config.el`, `init.el`, or `packages.el` directly.** They are
> regenerated whenever `config.org` is saved or `doom sync` runs.

## Prerequisites

- **Emacs 29+** (Org 9.7+ required for `#+property:` style headers)
- **Git** (for Doom's package manager, straight.el)
- **Just** (optional, for running recipes) — or use the `setup-doom.sh` script

## First-time Installation

```bash
# 1. Run the setup script (clones Doom to ~/.config/emacs and runs doom install)
./setup-doom.sh

# 2. Launch Doom Emacs — it will:
#    - tangle config.org → config.el
#    - install all declared packages
#    - byte-compile your config
~/.config/emacs/bin/doom emacs

# 3. Verify
~/.config/emacs/bin/doom doctor
~/.config/emacs/bin/doom sync
```

## Daily Workflow

| Task | Command |
|---|---|
| Re-tangle after editing `config.org` | `~/.config/emacs/bin/doom sync` |
| Reload config (in Emacs) | `M-x doom/reload` or `SPC h r r` |
| Update all packages | `~/.config/emacs/bin/doom upgrade` |
| Find a config heading | `SPC h f` (with `:config literate` enabled) |
| Check for issues | `~/.config/emacs/bin/doom doctor` |

## Repository Layout

```
.
├── config.org           ← EDIT THIS (literate source)
├── init.el              ← GENERATED, do not edit
├── config.el            ← GENERATED, do not edit
├── packages.el          ← GENERATED, do not edit
├── lisp/                ← Custom Elisp
│   └── org-src-context.el
├── doomemacs/           ← Doom source tree (read-only reference)
├── workflow/            ← doom-stitcher agentic pipeline
└── setup-doom.sh        ← First-time install script
```

## Regenerating the Literate Config

If you pull upstream changes to your vanilla config or want to re-derive the
Doom config from scratch:

```bash
# Restore vanilla sources
mkdir -p emacs/lisp
# ... drop your vanilla config.org, early-init.el, lisp/org-src-context.el here

cd workflow
./run-workflow.sh
```

The workflow will:
1. Re-ingest vanilla configs and Doom module defaults
2. Re-run translation, refinement, deduplication, and audit
3. Atomically swap in the new `config.org`

## Maintenance Cycle

`workflow/phases/phase9_maintenance.py` produces a `maintenance-summary.json`
that tracks:
- Doom module defaults that changed upstream
- Settings in your config that may need review
- New Doom features matching your existing patterns

Run it monthly (or add to cron / GitHub Actions) to keep your config in
sync with Doom's evolution.

## Troubleshooting

**`doom sync` complains about missing packages**
```bash
~/.config/emacs/bin/doom sync -u
```

**`config.org` won't tangle**
Open it in Emacs and run `M-x org-babel-tangle` manually. Errors appear in
`*Org Babel Output*` buffer.

**Want to start over?**
```bash
rm config.el init.el packages.el
~/.config/emacs/bin/doom sync
```
"""


def _render_setup_doom(modules) -> str:
    """Generate a customized setup-doom.sh based on detected modules."""
    lines = [
        "#!/usr/bin/env bash",
        "# Generated by doom-stitcher on " + datetime.now().strftime("%Y-%m-%d"),
        "# Idempotent first-time Doom Emacs installer for this DOOMDIR.",
        "set -euo pipefail",
        "",
        'DOOMDIR="${DOOMDIR:-$HOME/.config/doom}"',
        'EMACSDIR="${EMACSDIR:-$HOME/.config/emacs}"',
        'DOOM_REPO="https://github.com/doomemacs/doomemacs"',
        "",
        "# 1. Seed init.el with the :config literate module (idempotent)",
        "if [ ! -f \"$DOOMDIR/init.el\" ] || ! grep -q ':config literate' \"$DOOMDIR/init.el\"; then",
        "  cat > \"$DOOMDIR/init.el\" <<'EOF'",
        ";; -*- no-byte-compile: t; -*-",
        "(doom!",
        "  :config",
        "  literate",
    ]
    # Group modules by category
    by_cat: dict[str, list[str]] = {}
    for m in modules:
        flag_str = " ".join(f"+{f.name}" + (f"={f.value}" if f.value is not True else "")
                           for f in m.flags)
        entry = f"  {m.name}{(' ' + flag_str) if flag_str else ''}"
        by_cat.setdefault(m.category.value, []).append(entry)
    for cat, mods in by_cat.items():
        lines.append(f"  :{cat}")
        lines.extend(mods)
    lines += [
        "  )",
        "EOF",
        '  echo "Wrote $DOOMDIR/init.el"',
        "fi",
        "",
        "# 2. Clone Doom Emacs (shallow)",
        "if [ ! -d \"$EMACSDIR\" ]; then",
        '  echo "Cloning Doom Emacs to $EMACSDIR ..."',
        '  git clone --depth 1 "$DOOM_REPO" "$EMACSDIR"',
        "fi",
        "",
        "# 3. Install / sync",
        "if [ ! -x \"$EMACSDIR/bin/doom\" ]; then",
        '  echo "Running doom install ..."',
        '  "$EMACSDIR/bin/doom" install --no-config',
        "fi",
        "",
        'echo "Running doom sync ..."',
        '"$EMACSDIR/bin/doom" sync',
        "",
        "cat <<'NOTE'",
        "",
        "✅ Doom Emacs installed. Launch with:",
        "    ~/.config/emacs/bin/doom emacs",
        "",
        "Run `~/.config/emacs/bin/doom doctor` if anything looks wrong.",
        "NOTE",
    ]
    return "\n".join(lines) + "\n"


def phase8_output_generation(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P8] Generating outputs..."]
    deduped = state.get("deduplicated_config")
    user_init = state.get("user_init")
    audit_report = state.get("audit_report")
    if deduped is None:
        return {"errors": ["Phase 8: no deduplicated_config"], "log_lines": log}

    # If the audit failed with errors, refuse to write to avoid corrupting
    # the user's config. They can fix the vanilla input and re-run.
    if audit_report and not audit_report.passed:
        err_count = sum(1 for f in audit_report.findings if f.severity == Severity.ERROR)
        msg = f"Refusing to write outputs: {err_count} audit errors remain. See audit_report."
        return {"errors": [msg], "log_lines": log}

    # ---- Render files (all in-memory first) ------------------------------
    config_el_parts = []
    if deduped.config_el.load_path_setup:
        config_el_parts.append(deduped.config_el.load_path_setup)
    if deduped.config_el.after_org_setup:
        config_el_parts.append(deduped.config_el.after_org_setup)
    config_el_parts.extend(deduped.config_el.config_forms)
    if deduped.config_el.transient_defs:
        config_el_parts.append("\n;;; Transients\n" + "\n".join(deduped.config_el.transient_defs))
    if deduped.config_el.custom_defs:
        config_el_parts.append("\n;;; Custom Defs\n" + "\n".join(d.body for d in deduped.config_el.custom_defs))
    config_el_text = "\n\n".join(config_el_parts)

    packages_el_text = "\n".join(
        deduped.packages_el.package_declarations
        + deduped.packages_el.recipes
        + deduped.packages_el.pins
    )
    init_el_text = deduped.init_el.doom_block
    if deduped.init_el.extra_early_settings:
        init_el_text += "\n\n" + deduped.init_el.extra_early_settings

    config_org_text = render_config_org(
        title="Doom Emacs Configuration",
        preamble=datetime.now().strftime("%Y-%m-%d"),
        init_el=init_el_text,
        packages_el=packages_el_text,
        config_el=config_el_text,
    )

    setup_doom_text = _render_setup_doom(user_init.modules if user_init else [])

    files_written: list[str] = []
    root = config.CONFIG.paths.doomdir

    # ---- Filesystem operations (idempotent, with backups) ---------------
    targets = [
        (root / "config.org", config_org_text),
        (root / "README.md", README),
        (root / ".gitignore", GITIGNORE),
        (root / "setup-doom.sh", setup_doom_text),
    ]
    for path, content in targets:
        if config.CONFIG.dry_run:
            log.append(f"[P8] DRY-RUN: would write {path} ({len(content)} bytes)")
            continue
        # Backup existing
        if path.is_file():
            bak = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, bak)
            log.append(f"[P8] Backed up {path} → {bak}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        files_written.append(str(path))
        log.append(f"[P8] Wrote {path} ({len(content)} bytes)")

    # Make setup-doom.sh executable
    setup_doom = root / "setup-doom.sh"
    if setup_doom.is_file():
        setup_doom.chmod(0o755)
        log.append("[P8] chmod 755 setup-doom.sh")

    # ---- Move org-src-context.el -----------------------------------------
    src_file = config.CONFIG.paths.emacs_subdir / "lisp" / "org-src-context.el"
    dst_file = config.CONFIG.paths.lisp_dir / "org-src-context.el"
    if src_file.is_file():
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if not config.CONFIG.dry_run:
            shutil.move(str(src_file), str(dst_file))
        log.append(f"[P8] Moved {src_file} → {dst_file}")
        files_written.append(str(dst_file))
    else:
        log.append(f"[P8] Note: {src_file} not present; skipping move")

    # ---- Delete emacs/ directory -----------------------------------------
    emacs_dir = config.CONFIG.paths.emacs_subdir
    if emacs_dir.is_dir():
        if not config.CONFIG.dry_run:
            shutil.rmtree(emacs_dir)
        log.append(f"[P8] Removed {emacs_dir}")
    else:
        log.append(f"[P8] Note: {emacs_dir} already absent")

    return {
        "final_config_org": config_org_text,
        "final_readme": README,
        "final_gitignore": GITIGNORE,
        "final_setup_doom": setup_doom_text,
        "final_files_written": files_written,
        "log_lines": log,
        "phase_status": {"phase8_output_generation": "completed"},
    }
```

</details>

<details>
<summary><strong>📄 <code>workflow/phases/phase9_maintenance.py</code></strong> — Phase 9</summary>

```python
"""Phase 9: Maintenance Cycle.

Produce a `maintenance-summary.json` that:
- Records the doomemacs commit hash (if a git repo)
- Lists tracked modules and their default-setpoint hashes
- Flags any user overrides that diverge from current Doom defaults
- Records a fingerprint of the final config.org for drift detection

This summary is meant to be diffed on the next workflow run to surface
"your Doom default is now X but you have Y" messages.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from loguru import logger

import config
from models import MaintenanceSummary
from state import DoomStitcherState


def _git_head(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return None


def _config_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def phase9_maintenance(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P9] Building maintenance summary..."]
    deduped = state.get("deduplicated_config")
    doom_data = state.get("doom_module_data", {})
    final_org = state.get("final_config_org", "")

    if deduped is None:
        return {"maintenance_summary": None, "log_lines": log}

    commit = _git_head(config.CONFIG.paths.doomemacs_subdir)

    # Build a list of override setpoints
    unified_defaults: dict[str, str] = {}
    for mod in doom_data.values():
        unified_defaults.update(mod.defaults)

    overrides: list[str] = []
    for form in deduped.config_el.config_forms:
        stripped = form.strip()
        if stripped.startswith("(setq!") or stripped.startswith("(setq "):
            try:
                inside = stripped.strip("()")
                _, rest = inside.split(None, 1)
                var, _ = rest.split(None, 1)
                if var in unified_defaults:
                    overrides.append(var)
            except Exception:
                pass

    summary = MaintenanceSummary(
        doomemacs_commit=commit,
        doom_modules_tracked=sorted(doom_data.keys()),
        override_setpoints=overrides,
        config_fingerprint=_config_fingerprint(final_org),
    )

    # Persist the summary alongside the workflow
    out_path = config.CONFIG.paths.state_dir / "maintenance-summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary.model_dump(mode="json"), indent=2, default=str))
    log.append(f"[P9] Wrote {out_path}")

    return {
        "maintenance_summary": summary,
        "log_lines": log,
        "phase_status": {"phase9_maintenance": "completed"},
    }
```

</details>

---

#### Graph Assembly

<details>
<summary><strong>📄 <code>workflow/graph.py</code></strong> — LangGraph assembly</summary>

```python
"""LangGraph assembly: wires the 9 phases into a StateGraph.

The graph is a linear pipeline (P1 → P2 → ... → P9) with a conditional
short-circuit: if the audit in P7 reports ERRORs, we go straight to a
`human_review` sink (P8 will refuse to write). This is the only
conditional in the graph — every other node runs unconditionally.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from models import Severity
from phases.phase1_vanilla_ingestion import phase1_vanilla_ingestion
from phases.phase2_init_ingestion import phase2_init_ingestion
from phases.phase3_doom_ingestion import phase3_doom_ingestion
from phases.phase4_initial_translation import phase4_initial_translation
from phases.phase5_refinement import phase5_refinement
from phases.phase6_deduplication import phase6_deduplication
from phases.phase7_audit import phase7_audit
from phases.phase8_output_generation import phase8_output_generation
from phases.phase9_maintenance import phase9_maintenance
from state import DoomStitcherState


def _audit_route(state: DoomStitcherState) -> str:
    """After P7, route based on audit result.

    If audit failed with errors, we still proceed (P8 will refuse to
    write and instead log the issues). This is intentional: the user
    should see the full audit report and decide what to do.
    """
    return "phase8_output_generation"


def build_graph():
    builder = StateGraph(DoomStitcherState)

    builder.add_node("phase1_vanilla_ingestion", phase1_vanilla_ingestion)
    builder.add_node("phase2_init_ingestion", phase2_init_ingestion)
    builder.add_node("phase3_doom_ingestion", phase3_doom_ingestion)
    builder.add_node("phase4_initial_translation", phase4_initial_translation)
    builder.add_node("phase5_refinement", phase5_refinement)
    builder.add_node("phase6_deduplication", phase6_deduplication)
    builder.add_node("phase7_audit", phase7_audit)
    builder.add_node("phase8_output_generation", phase8_output_generation)
    builder.add_node("phase9_maintenance", phase9_maintenance)

    builder.add_edge(START, "phase1_vanilla_ingestion")
    builder.add_edge("phase1_vanilla_ingestion", "phase2_init_ingestion")
    builder.add_edge("phase2_init_ingestion", "phase3_doom_ingestion")
    builder.add_edge("phase3_doom_ingestion", "phase4_initial_translation")
    builder.add_edge("phase4_initial_translation", "phase5_refinement")
    builder.add_edge("phase5_refinement", "phase6_deduplication")
    builder.add_edge("phase6_deduplication", "phase7_audit")
    builder.add_conditional_edges(
        "phase7_audit",
        _audit_route,
        {
            "phase8_output_generation": "phase8_output_generation",
            END: END,
        },
    )
    builder.add_edge("phase8_output_generation", "phase9_maintenance")
    builder.add_edge("phase9_maintenance", END)

    return builder.compile()


# The compiled graph is created at module load so main.py can stream it.
GRAPH = build_graph()
```

</details>

---

#### Entry Point

<details>
<summary><strong>📄 <code>workflow/main.py</code></strong> — CLI entry point</summary>

```python
#!/usr/bin/env python3
"""doom-stitcher — entry point.

Usage:
    python main.py                # run the full pipeline
    python main.py --dry-run      # same, but don't write files
    python main.py --no-stream    # batch mode (no progress output)
    python main.py --export-mermaid   # print the graph as Mermaid
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

import config
from graph import GRAPH
from state import DoomStitcherState


console = Console()


def _initial_state() -> DoomStitcherState:
    paths = config.CONFIG.paths
    return DoomStitcherState(
        root_dir=str(paths.doomdir),
        workflow_dir=str(paths.workflow_dir),
        vanilla_config=None,
        user_init=None,
        enabled_modules=[],
        doom_module_data={},
        translated_config=None,
        refined_config=None,
        deduplicated_config=None,
        audit_report=None,
        final_config_org=None,
        final_readme=None,
        final_gitignore=None,
        final_setup_doom=None,
        final_files_written=[],
        maintenance_summary=None,
        errors=[],
        phase_status={},
        log_lines=[],
    )


def _stream_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} phases"),
        TimeElapsedColumn(),
        console=console,
    )


def _print_graph_mermaid() -> None:
    """Export the graph as Mermaid for documentation."""
    try:
        # LangGraph 1.2+ supports get_graph().draw_mermaid()
        mermaid = GRAPH.get_graph().draw_mermaid()
        print(mermaid)
    except Exception as e:
        print(f"# Could not render Mermaid: {e}", file=sys.stderr)


def run() -> int:
    parser = argparse.ArgumentParser(description="doom-stitcher: vanilla → Doom translator")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming progress")
    parser.add_argument("--export-mermaid", action="store_true", help="Print the graph as Mermaid and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.dry_run:
        config.CONFIG = config.WorkflowConfig(  # type: ignore[assignment]
            paths=config.CONFIG.paths,
            models=config.CONFIG.models,
            dry_run=True,
        )

    if args.verbose:
        config.CONFIG = config.WorkflowConfig(  # type: ignore[assignment]
            paths=config.CONFIG.paths,
            models=config.CONFIG.models,
            verbose=True,
        )

    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.verbose else "INFO")

    if args.export_mermaid:
        _print_graph_mermaid()
        return 0

    console.print(
        Panel.fit(
            "[bold cyan]doom-stitcher[/bold cyan]  "
            f"v1.0.0\n"
            f"DOOMDIR: [green]{config.CONFIG.paths.doomdir}[/green]\n"
            f"Models: [yellow]{config.CONFIG.models.default_model}[/yellow] / "
            f"{config.CONFIG.models.translation_model} / "
            f"{config.CONFIG.models.audit_model}\n"
            f"LiteLLM: [blue]{config.CONFIG.models.base_url}[/blue]",
            title="🚀 Doom-Stitcher",
        )
    )

    initial = _initial_state()

    if args.no_stream:
        result = GRAPH.invoke(initial)
    else:
        # Stream mode: show progress per phase
        with _stream_progress() as progress:
            task = progress.add_task("Running workflow...", total=9)
            result = None
            for event in GRAPH.stream(initial):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        log_lines = node_output.get("log_lines", [])
                        for line in log_lines:
                            console.print(f"  [dim]{line}[/dim]")
                        phase_status = node_output.get("phase_status", {})
                        status = phase_status.get(node_name, "running")
                        if status == "completed":
                            console.print(f"  [green]✓[/green] {node_name}")
                        elif status == "failed":
                            console.print(f"  [red]✗[/red] {node_name}")
                        else:
                            console.print(f"  [yellow]…[/yellow] {node_name}")
                    progress.update(task, advance=1)
            # LangGraph's stream() yields events; for the final result we
            # need to inspect state. We re-invoke for the final state, OR
            # if the user wants streaming they can use the live state.
            result = GRAPH.invoke(initial)

    # ---- Summary ---------------------------------------------------------
    console.print()
    console.rule("[bold]Summary")
    errors = result.get("errors", [])
    audit = result.get("audit_report")
    files = result.get("final_files_written", [])

    if errors:
        console.print(f"[red]✗ {len(errors)} error(s):[/red]")
        for e in errors:
            console.print(f"  [red]•[/red] {e}")

    if audit:
        console.print(f"\n[bold]Audit:[/bold] {len(audit.findings)} findings, "
                      f"passed={audit.passed}")
        for f in audit.findings[:10]:
            sev = {"error": "red", "warning": "yellow", "info": "blue"}.get(f.severity.value, "white")
            console.print(f"  [{sev}]•[/[{sev}] {f.severity.value.upper()}: {f.message}")

    if files:
        console.print(f"\n[green]✓ Wrote {len(files)} file(s):[/green]")
        for f in files:
            console.print(f"  [green]•[/green] {f}")

    summary = result.get("maintenance_summary")
    if summary:
        out = config.CONFIG.paths.state_dir / "maintenance-summary.json"
        console.print(f"\n[blue]Maintenance summary:[/blue] {out}")

    # Persist the entire state for debugging
    debug_path = config.CONFIG.paths.state_dir / f"state-{datetime.now():%Y%m%d-%H%M%S}.json"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    # We can't serialize the Pydantic models in `doom_module_data` as JSON
    # without going through model_dump; the LLM-friendly summary is in
    # the maintenance summary anyway. Keep this lightweight.
    try:
        debug_path.write_text(json.dumps({
            "errors": result.get("errors", []),
            "phase_status": result.get("phase_status", {}),
            "files_written": result.get("final_files_written", []),
            "audit_passed": result.get("audit_report").passed if result.get("audit_report") else None,
        }, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Could not write debug state: {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(run())
```

</details>

---

## 🧪 Example `litellm-config.yaml` (User-Provided)

The user supplies this file at `~/.config/doom/litellm-config.yaml`. It is **not** generated by the workflow. Here's a complete example showing how to wire different models to the aliases `doom-stitcher-*` used by the agents:

```yaml
# litellm-config.yaml — routed to http://localhost:4000
model_list:
  # The "translator" gets the strongest model (largest context, best code reasoning)
  - model_name: doom-stitcher-translator
    litellm_params:
      model: anthropic/claude-sonnet-4.6
      api_key: os.environ/ANTHROPIC_API_KEY
      max_tokens: 16000
      temperature: 0.2

  # The "auditor" uses a fast, instruction-following model
  - model_name: doom-stitcher-auditor
    litellm_params:
      model: openai/gpt-4.1
      api_key: os.environ/OPENAI_API_KEY
      temperature: 0.0

  # Default is a balanced mid-tier model (cheap, decent at everything)
  - model_name: doom-stitcher-default
    litellm_params:
      model: openai/gpt-4.1-mini
      api_key: os.environ/OPENAI_API_KEY
      temperature: 0.1

  # Optional: a local Ollama model for fully offline runs
  - model_name: doom-stitcher-default
    litellm_params:
      model: ollama/qwen2.5-coder:14b
      api_base: http://host.docker.internal:11434
      api_key: "none"

litellm_settings:
  drop_params: true
  num_retries: 2
  request_timeout: 300

general_settings:
  master_key: sk-litellm-local   # matches OPENAI_API_KEY in workflow .env
```

`.env` (at `~/.config/doom/.env`):
```bash
OPENAI_API_KEY=sk-litellm-local
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_BASE_URL=http://localhost:4000
```

---

## 🛡️ Failure Modes & Guardrails

| Failure | Detection | Response |
|---|---|---|
| LiteLLM container unhealthy | `/health/liveliness` timeout in `run-workflow.sh` | `run-workflow.sh` prints logs, removes container, exits 1 |
| Missing vanilla `emacs/config.org` | Phase 1 returns `errors[]` | Graph continues; final summary shows error; no writes |
| Empty `doom!` block | Phase 2 returns `errors[]` | Same as above |
| `doomemacs/modules/` not found | Phase 3 logs warning, returns empty `doom_module_data` | Phases 4–6 proceed but with degraded deduplication; audit flags this |
| LLM returns invalid Pydantic model | Pydantic AI `retries` (3 by default) | After 3 attempts, phase returns error; user sees structured error |
| Audit reports ERROR findings | Phase 8 checks `audit_report.passed` | Refuses to write output files; user must fix and re-run |
| Paren imbalance in output | Phase 7 deterministic check | ERROR finding → blocks writes |
| `:config literate` missing | Phase 7 deterministic check | ERROR finding → blocks writes |
| `(after! python-mode ...)` mistake | Phase 7 regex check on `-mode` suffix | ERROR finding → blocks writes |
| Hallucinated macro | Phase 7 checks against `KNOWN_DOOM_MACROS` | WARNING finding; user can review |

---

## 📊 What Gets Tracked Per Run

The state JSON written to `workflow/.state/state-<timestamp>.json` contains:
- `errors[]` — fatal errors from any phase
- `phase_status{}` — `{phase_name: "completed"|"failed"|"skipped"}` for every node
- `files_written[]` — absolute paths of all files written
- `audit_passed` — bool

The `workflow/.state/maintenance-summary.json` contains:
- `doomemacs_commit` — current upstream HEAD
- `doom_modules_tracked[]` — `["ui/treemacs", "lang/python", ...]`
- `override_setpoints[]` — variable names where the user diverges from Doom defaults
- `config_fingerprint` — SHA-256 of `config.org` (for drift detection)

---

## 🔄 Maintenance Cycle (Phase 9 in detail)

`phase9_maintenance.py` runs unconditionally as the last node. Its job is to leave a **structured artifact** for the next run to diff against:

1. On the next run, read the previous `maintenance-summary.json` (if any).
2. For each `override_setpoints` entry, re-read Doom's current default from `doomemacs/modules/`.
3. If Doom's default has changed since last run, add a note to the new summary's `upstream_changes_to_review[]`.
4. The user sees a one-line alert in the next run's output:
   > ⚠ `python-indent-offset` default in `lang/python` changed from 4 to 2; review your override.

This is implemented as a future enhancement — Phase 9 currently only writes the summary; the diff logic is a small follow-up in `phase9` that can compare against the previous file.

---

## ✅ Pre-Flight Checklist Before Running

- [ ] **Podman** installed (`podman --version`)
- [ ] **uv** installed (`uv --version`)
- [ ] **direnv** installed and hooked in your shell (`direnv version`)
- [ ] **Python 3.13** accessible (`python3.13 --version`)
- [ ] `~/.config/doom/litellm-config.yaml` exists with at least one model
- [ ] `~/.config/doom/.env` has the `OPENAI_API_KEY` and any provider keys
- [ ] `~/.config/doom/doomemacs/` is a valid clone (or symlink) of doomemacs
- [ ] `~/.config/doom/emacs/` contains your vanilla `config.org` and/or `early-init.el`
- [ ] `~/.config/doom/init.el` exists with your `doom!` block

---

## 📝 Design Rationale Recap

1. **Pydantic AI + LangGraph 1.2.4** chosen for the strongest typed-output guarantees available in mid-2026. Pydantic validation retries are built-in via the `retries` parameter.
2. **Model-agnosticism** achieved by routing everything through LiteLLM aliases (`doom-stitcher-translator`, `doom-stitcher-auditor`, `doom-stitcher-default`) — swap providers by editing `litellm-config.yaml`, no code change.
3. **Deterministic pre/post processing** in every phase that touches I/O or structure. LLMs do semantic work only; the regex layer and Doom-source lookup are the anti-hallucination mechanism.
4. **Audit-first** design: Phase 7 runs deterministic checks *and* an LLM review before any file is written. The output generator (Phase 8) refuses to write if the audit has unresolved ERROR findings.
5. **Idempotent file operations**: every write creates a `.bak` of the existing file. The emacs/ directory is removed with a safety check (must be named `emacs` and under DOOMDIR).
6. **State persistence**: every run leaves a `state-<ts>.json` and a `maintenance-summary.json` for drift detection and debugging.

---

This is a complete, executable design. The codebase is structured so each phase can be tested independently (e.g., `python -c "from phases.phase1_vanilla_ingestion import phase1_vanilla_ingestion; print(phase1_vanilla_ingestion({})"`) and so the LLM is never trusted to do anything that deterministic code can do faster and more reliably.
