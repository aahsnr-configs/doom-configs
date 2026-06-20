# doom-stitcher

## `__init__.py`

**Path:** `~/.config/doom/workflow/phases/__init__.py`

```python
"""Phase node functions exposed to LangGraph.

Each phase is a pure (or near-pure) function: (state) -> partial_state_update. LLM calls happen via the shared agent instances in agents.py.

~/.config/doom/workflow/phases/__init__.py
"""
```

## `agents.py`

**Path:** `~/.config/doom/workflow/agents.py`

```python
"""Pydantic AI agent factories.

Each agent is a stateless runner constructed from the runtime config. We use OpenAIChatModel + OpenAIProvider so the LiteLLM proxy is the sole model endpoint. The model_name strings are aliases defined in the user's litellm-config.yaml.

~/.config/doom/workflow/agents.py
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
from tools import get_agent_tools

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

## `config.py`

**Path:** `~/.config/doom/workflow/config.py`

```python
"""Centralized configuration for doom-stitcher.

All paths and model selections come from environment variables. The workflow is fully model-agnostic: model names are passed through verbatim to the LiteLLM proxy, which resolves them via its own config.yaml.

Secrets and paths live in `.env` at the repo root, encrypted with dotenvx.
This module does NOT read or decrypt `.env` itself -- it expects the
process to already have been launched via `dotenvx run -f "$DOOMDIR/.env"
-- ...` (see flake.nix), which injects plaintext values into the
environment before Python even starts.

~/.config/doom/workflow/config.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Required env var {name} is not set")
    if val and val.startswith("encrypted:"):
        raise RuntimeError(
            f"Env var {name} is still dotenvx-encrypted ciphertext. "
            "Run via `nix run` / `nix run .#workflow`, or wrap your "
            'command with `dotenvx run -f "$DOOMDIR/.env" -- ...` so '
            "secrets are decrypted before the workflow starts."
        )
    return val or ""


@dataclass(frozen=True)
class Paths:
    """Filesystem layout rooted at DOOMDIR."""

    doomdir: Path = field(
        default_factory=lambda: Path(
            _env("DOOMDIR", str(Path.home() / ".config/doom"))
        ).expanduser()
    )
    workflow_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    emacs_subdir: Path = field(init=False)
    doomemacs_subdir: Path = field(init=False)
    modules_dir: Path = field(init=False)
    lisp_dir: Path = field(init=False)
    state_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        # Derive `emacs/` and `doomemacs/` from `doomdir` rather than
        # re-reading DOOMDIR with an empty-string default. The old
        # `_env("DOOMDIR", "") + "/emacs"` produced bogus *absolute* paths
        # like `/emacs` and `/doomemacs` whenever DOOMDIR was unset, instead
        # of falling back to `~/.config/doom/emacs` like `doomdir` does.
        object.__setattr__(self, "emacs_subdir", self.doomdir / "emacs")
        object.__setattr__(self, "doomemacs_subdir", self.doomdir / "doomemacs")
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

    base_url: str = field(
        default_factory=lambda: _env("OPENAI_BASE_URL", "http://localhost:4000")
    )
    # Pydantic AI sends this as the `Authorization: Bearer <api_key>` header
    # to the LiteLLM proxy. The proxy validates it against
    # `general_settings.master_key` (LITELLM_MASTER_KEY). Rather than
    # requiring a *second*, separately-managed `OPENAI_API_KEY` value that
    # must be kept in sync with LITELLM_MASTER_KEY, fall back to
    # LITELLM_MASTER_KEY directly -- the same `.env` value the proxy itself
    # uses. Set OPENAI_API_KEY explicitly only if you want the workflow to
    # authenticate with a scoped virtual key instead of the master key.
    api_key: str = field(
        default_factory=lambda: _env(
            "OPENAI_API_KEY", _env("LITELLM_MASTER_KEY", "sk-litellm-local")
        )
    )

    # Per-role model selection. Each role can be tuned independently.
    default_model: str = field(
        default_factory=lambda: _env(
            "DOOM_STITCHER_MODEL_DEFAULT", "doom-stitcher-default"
        )
    )
    translation_model: str = field(
        default_factory=lambda: _env(
            "DOOM_STITCHER_MODEL_TRANSLATION", "doom-stitcher-translator"
        )
    )
    audit_model: str = field(
        default_factory=lambda: _env(
            "DOOM_STITCHER_MODEL_AUDIT", "doom-stitcher-auditor"
        )
    )
    extraction_model: str = field(
        default_factory=lambda: _env(
            "DOOM_STITCHER_MODEL_EXTRACTION", "doom-stitcher-default"
        )
    )


@dataclass(frozen=True)
class WorkflowConfig:
    paths: Paths = field(default_factory=Paths)
    models: ModelConfig = field(default_factory=ModelConfig)

    # Operational toggles
    verbose: bool = field(
        default_factory=lambda: _env("DOOM_STITCHER_VERBOSE", "0") == "1"
    )
    dry_run: bool = field(
        default_factory=lambda: _env("DOOM_STITCHER_DRY_RUN", "0") == "1"
    )
    skip_maintenance: bool = field(
        default_factory=lambda: _env("DOOM_STITCHER_SKIP_MAINTENANCE", "0") == "1"
    )


CONFIG = WorkflowConfig()
```

## `directive.xml`

**Path:** `~/.config/doom/workflow/prompts/directive.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
  Doom-Stitcher base runtime directive.
  Loaded once at workflow startup by workflow.prompt.
  The <content> CDATA block is sent verbatim as the LLM system prompt.
  Storing it as XML (rather than a Python triple-quoted string) avoids
  parser conflicts with markdown triple-backticks, escaped backslashes,
  and f-string braces that appear in the directive body.
-->
<directive id="doom-stitcher" version="1.0" format="markdown">
  <metadata>
    <title>Runtime Directive for the Vanilla-to-Doom Translation Agent</title>
    <agent>Doom-Stitcher Agent</agent>
    <phase>all</phase>
  </metadata>
  <content><![CDATA[
# Runtime Directive for the Vanilla-to-Doom Translation Agent

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
]]></content>
</directive>
```

## `elisp.py`

**Path:** `~/.config/doom/workflow/utils/elisp.py`

```python
"""Lightweight, regex-based Elisp parsing.

We deliberately avoid full S-expression parsing — it adds a heavy dep
(sexpdata, sexp_parser) for limited gain. Doom configs follow conventions
that regex handles well: `(defun NAME`, `(defcustom NAME`, `(setq VAR`,
`(package! NAME ...)`, `(after! FEATURE`, `(map! ...)`, etc.

~/.config/doom/workflow/utils/elisp.py
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

## `graph.py`

**Path:** `~/.config/doom/workflow/graph.py`

```python
"""LangGraph assembly: wires the 9 phases into a StateGraph.

The graph is a linear pipeline (P1 → P2 → ... → P9). P7 (audit) always
flows into P8 (output generation); P8 itself is the audit gate -- if
`audit_report.passed` is False, P8 logs the audit errors and refuses to
write any files, but the graph still continues to P9 so a maintenance
summary is produced for the (unwritten) run.

~/.config/doom/workflow/graph.py
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from phases.phase9_maintenance import phase9_maintenance

from phases.phase1_vanilla_ingestion import phase1_vanilla_ingestion
from phases.phase2_init_ingestion import phase2_init_ingestion
from phases.phase3_doom_ingestion import phase3_doom_ingestion
from phases.phase4_initial_translation import phase4_initial_translation
from phases.phase5_refinement import phase5_refinement
from phases.phase6_deduplication import phase6_deduplication
from phases.phase7_audit import phase7_audit
from phases.phase8_output_generation import phase8_output_generation
from state import DoomStitcherState


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
    builder.add_edge("phase7_audit", "phase8_output_generation")
    builder.add_edge("phase8_output_generation", "phase9_maintenance")
    builder.add_edge("phase9_maintenance", END)

    return builder.compile()


# The compiled graph is created at module load so main.py can stream it.
GRAPH = build_graph()
```

## `main.py`

**Path:** `~/.config/doom/workflow/main.py`

```python
#!/usr/bin/env python3
"""doom-stitcher — entry point.

Usage:
    python main.py                # run the full pipeline
    python main.py --dry-run      # same, but don't write files
    python main.py --no-stream    # batch mode (no live progress)
    python main.py --export-mermaid   # print the graph as Mermaid

~/.config/doom/workflow/main.py
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


def _apply_overrides(*, dry_run: bool, verbose: bool) -> None:
    """Rebuild the frozen ``WorkflowConfig`` if CLI flags changed it.

    Because ``WorkflowConfig`` is frozen, we must construct a new instance
    rather than mutate. ``paths`` and ``models`` are carried over unchanged.
    """
    current = config.CONFIG
    if dry_run == current.dry_run and verbose == current.verbose:
        return  # no-op; avoid rebuilding for nothing
    new_cfg = config.WorkflowConfig(
        paths=current.paths,
        models=current.models,
        verbose=verbose,
        dry_run=dry_run,
        skip_maintenance=current.skip_maintenance,
    )
    # Reassigning the module attribute is safe; every subsequent
    # ``config.CONFIG`` read in this process will see the new value.
    config.CONFIG = new_cfg


def _print_graph_mermaid() -> None:
    """Export the graph as Mermaid for documentation."""
    try:
        # LangGraph 1.2.x: get_graph() returns a Graph; draw_mermaid() returns str
        mermaid = GRAPH.get_graph().draw_mermaid()
        print(mermaid)
    except Exception as e:
        print(f"# Could not render Mermaid: {e}", file=sys.stderr)


def _serialize_audit_passed(result: DoomStitcherState) -> bool | None:
    """Safely extract audit_report.passed regardless of dict vs model object."""
    audit = result.get("audit_report")
    if audit is None:
        return None
    return getattr(audit, "passed", None)


def run() -> int:
    parser = argparse.ArgumentParser(
        description="doom-stitcher: vanilla → Doom translator"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not write output files"
    )
    parser.add_argument(
        "--no-stream", action="store_true", help="Disable streaming progress"
    )
    parser.add_argument(
        "--export-mermaid",
        action="store_true",
        help="Print the graph as Mermaid and exit",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    _apply_overrides(dry_run=args.dry_run, verbose=args.verbose)

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

    # Run the workflow ONCE. ``stream_mode="values"`` yields the full state
    # after each node, so the last value is the final state. Do NOT also
    # call ``invoke`` afterwards — that would re-run the whole pipeline.
    if args.no_stream:
        result = GRAPH.invoke(initial)
        for line in result.get("log_lines", []):
            console.print(f"  [dim]{line}[/dim]")
    else:
        result = initial
        with console.status(
            "[bold green]Running workflow…[/bold green]", spinner="dots"
        ):
            for state in GRAPH.stream(initial, stream_mode="values"):
                result = state
                # Stream each phase's log lines as they arrive
                for line in state.get("log_lines", []):
                    console.print(f"  [dim]{line}[/dim]")

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

    if audit is not None:
        console.print(
            f"\n[bold]Audit:[/bold] {len(audit.findings)} findings, "
            f"passed={audit.passed}"
        )
        for f in audit.findings[:10]:
            sev = getattr(f.severity, "value", str(f.severity))
            color = {"error": "red", "warning": "yellow", "info": "blue"}.get(
                sev, "white"
            )
            console.print(f"  [{color}]•[/{color}] {sev.upper()}: {f.message}")

    if files:
        console.print(f"\n[green]✓ Wrote {len(files)} file(s):[/green]")
        for f in files:
            console.print(f"  [green]•[/green] {f}")

    summary = result.get("maintenance_summary")
    if summary is not None:
        out = config.CONFIG.paths.state_dir / "maintenance-summary.json"
        console.print(f"\n[blue]Maintenance summary:[/blue] {out}")

    # Persist lightweight debug state (avoid serializing Pydantic models)
    debug_path = (
        config.CONFIG.paths.state_dir / f"state-{datetime.now():%Y%m%d-%H%M%S}.json"
    )
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        debug_path.write_text(
            json.dumps(
                {
                    "errors": list(result.get("errors", [])),
                    "phase_status": dict(result.get("phase_status", {})),
                    "files_written": list(result.get("final_files_written", [])),
                    "audit_passed": _serialize_audit_passed(result),
                },
                indent=2,
            )
        )
    except Exception as e:
        logger.warning(f"Could not write debug state: {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(run())
```

## `models.py`

**Path:** `~/.config/doom/workflow/models.py`

```python
"""Pydantic v2 models representing every typed payload in the workflow.

These are the contracts that flow through LangGraph state. Every agent's output is validated against one of these models, ensuring the LLM cannot inject malformed data into the next phase.

~/.config/doom/workflow/models.py
"""

from __future__ import annotations

from datetime import datetime, timezone
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

    kind: Literal[
        "defun",
        "defmacro",
        "defhydra",
        "defvar",
        "defcustom",
        "transient",
        "advice",
        "other",
    ]
    name: str
    body: str
    source_location: str | None = None  # e.g. "emacs/config.org::Custom defuns"


class VanillaConfig(BaseModel):
    """Aggregate of everything extracted from the vanilla configs."""

    packages: list[VanillaPackage] = Field(default_factory=list)
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)
    custom_defs: list[VanillaCustomDef] = Field(default_factory=list)
    early_init_settings: list[str] = Field(
        default_factory=list
    )  # raw early-init.el lines
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
    relevant_sections: list[str] = Field(
        default_factory=list
    )  # names of defuns/sections we care about


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

    package_declarations: list[str] = Field(
        default_factory=list
    )  # each a (package! ...) form
    recipes: list[str] = Field(default_factory=list)  # each a (recipe! ...) form
    pins: list[str] = Field(default_factory=list)  # each a (pin ...) form


class ConfigElBlock(BaseModel):
    """The config.el source block content."""

    load_path_setup: str = ""
    after_org_setup: str = ""  # contains (require 'org-src-context)
    config_forms: list[str] = Field(
        default_factory=list
    )  # each a (after! ...)/(use-package! ...)/(setq ...)
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
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    doomemacs_commit: str | None = None
    doom_modules_tracked: list[str] = Field(default_factory=list)
    override_setpoints: list[str] = Field(
        default_factory=list
    )  # settings that explicitly override Doom defaults
    upstream_changes_to_review: list[str] = Field(default_factory=list)
    config_fingerprint: str  # hash of final config.org, used to detect drift

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

## `org.py`

**Path:** `~/.config/doom/workflow/utils/org.py`

```python
"""Org-mode minimal parser for tangle-aware blocks.

~/.config/doom/workflow/utils/org.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_BEGIN_SRC = re.compile(
    r"""^\#\+BEGIN_SRC\s+(?P<lang>[\w-]+)?\s*(?::[ \t]*(?P<header>.*?))?$""",
    re.MULTILINE | re.IGNORECASE,
)
_END_SRC = re.compile(r"^\#\+END_SRC\s*$", re.MULTILINE | re.IGNORECASE)


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
    """Read the top-of-file #+PROPERTY: lines (case-insensitive directive)."""
    out: dict[str, str] = {}
    for line in org_text.splitlines():
        if line[:11].upper() == "#+PROPERTY:":
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

## `phase1_vanilla_ingestion.py`

**Path:** `~/.config/doom/workflow/phases/phase1_vanilla_ingestion.py`

````python
"""Phase 1: Vanilla Ingestion.

Parse emacs/config.org and emacs/early-init.el to extract:
- Package declarations (use-package, package-install, etc.)
- Keybindings (global-set-key, define-key, map!)
- Custom defuns/macros/hydras/transients
- early-init.el raw settings

Strategy: deterministic regex pre-extraction + LLM semantic enrichment on the org-mode src blocks.

~/.config/doom/workflow/phases/phase1_vanilla_ingestion.py
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

import config
from agents import VANILLA_INGESTION_AGENT
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
        log.append(
            f"[P1] LLM produced {len(vanilla.packages)} packages, "
            f"{len(vanilla.keybindings)} keybindings, {len(vanilla.custom_defs)} custom defs"
        )
        phase_status["phase1_vanilla_ingestion"] = "completed"
        return {
            "vanilla_config": vanilla,
            "log_lines": log,
            "phase_status": phase_status,
        }
    except Exception as e:
        logger.exception("Phase 1 LLM call failed")
        return {
            "vanilla_config": None,
            "errors": [f"Phase 1 failed: {e}"],
            "log_lines": log,
            "phase_status": {"phase1_vanilla_ingestion": "failed"},
        }
````

## `phase2_init_ingestion.py`

**Path:** `~/.config/doom/workflow/phases/phase2_init_ingestion.py`

````python
"""Phase 2: User init.el Ingestion.

Parse the user-provided `init.el` to identify which Doom modules are
enabled and with what flags. This drives Phase 3's module ingestion.

~/.config/doom/workflow/phases/phase2_init_ingestion.py
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
````

## `phase3_doom_ingestion.py`

**Path:** `~/.config/doom/workflow/phases/phase3_doom_ingestion.py`

```python
"""Phase 3: Doom Module Ingestion.

For each enabled module from Phase 2, read its files from
`doomemacs/modules/<category>/<name>/{config,init,packages}.el` and
extract a `DoomModuleData` summary.

The agent does semantic summarization; we pre-populate the deterministic
fields (defaults, packages) via regex extraction.

~/.config/doom/workflow/phases/phase3_doom_ingestion.py
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

## `phase4_hints.xml`

**Path:** `~/.config/doom/workflow/prompts/phase4_hints.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<directive id="phase4-translation" version="1.0" format="markdown">
  <metadata>
    <title>Phase 4 — Initial Translation (Pass 1) — Additional Context</title>
    <phase>4</phase>
  </metadata>
  <content><![CDATA[
## Phase 4 — Initial Translation (Pass 1) — Additional Context

When generating the `config.org` skeleton, use the following tangle rules:

- Default `# tangle` target is `config.el`.
- Use `:tangle packages.el` for the package manifest block.
- Use `:tangle init.el` for the `doom!` macro block.
- Add a global `#+property: header-args:emacs-lisp :tangle <file>` for each of the three targets so child src blocks inherit the correct tangle.

Recommended `#+property` header at the top of `config.org`:

#+property: header-args:emacs-lisp :tangle config.el :results none :lexical t
#+property: header-args:emacs-lisp :tangle packages.el :results none :lexical t
#+property: header-args:emacs-lisp :tangle init.el :results none :lexical t

For each vanilla package, produce a `(package! <name>)` form tangled to `packages.el`. For each `setq`, produce a `(setq ...)` or `(setq-hook! ...)` form inside the appropriate `(after! <feature> ...)` block in `config.el`.
]]></content>
</directive>
```

## `phase4_initial_translation.py`

**Path:** `~/.config/doom/workflow/phases/phase4_initial_translation.py`

````python
"""Phase 4: Initial Translation (Pass 1).

Translate vanilla idioms into Doom idioms, producing the first complete
`TranslatedConfig` with init.el, packages.el, and config.el blocks.

~/.config/doom/workflow/phases/phase4_initial_translation.py
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
````

## `phase5_hints.xml`

**Path:** `~/.config/doom/workflow/prompts/phase5_hints.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<directive id="phase5-refinement" version="1.0" format="markdown">
  <metadata>
    <title>Phase 5 — Refinement — Additional Context</title>
    <phase>5</phase>
  </metadata>
  <content><![CDATA[
## Phase 5 — Refinement — Additional Context

After the initial Pass-1 translation, perform these deterministic edits before calling the LLM:

1. Add this boilerplate to the very top of the `config.el` source block (before any user code):

   (add-to-list 'load-path (expand-file-name "lisp/" doom-user-dir))

2. Add an `(after! org ...)` block (inside `config.el` content) that does:

   (after! org
     (require 'org-src-context))

3. Transients: if vanilla used `defhydra`, `transient.define`, or `easy-hydra`, port them to Doom's `def-hydra!` and bind keys with `map!`.
4. Honor `early-init.el` settings by emitting them under a `:tangle early-init.el` source block only when strictly necessary.
]]></content>
</directive>
```

## `phase5_refinement.py`

**Path:** `~/.config/doom/workflow/phases/phase5_refinement.py`

````python
"""Phase 5: Refinement & Custom Elisp (Pass 2).

Integrate `org-src-context.el`, refine transients, and explicitly
override Doom defaults only where the vanilla config truly diverges.

~/.config/doom/workflow/phases/phase5_refinement.py
"""
from __future__ import annotations

from loguru import logger

from agents import REFINEMENT_AGENT
from state import DoomStitcherState


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
    except Exception:
        logger.exception("Phase 5 LLM call failed; keeping deterministic refinement")
        return {
            "refined_config": translated,
            "log_lines": log,
            "phase_status": {"phase5_refinement": "partial"},
        }
````

## `phase6_deduplication.py`

**Path:** `~/.config/doom/workflow/phases/phase6_deduplication.py`

```python
"""Phase 6: Deduplication.

Strip `package!` declarations that already exist in Doom's ingested module
defaults, and remove `setq` configurations that match Doom's defaults
exactly. This is a deterministic post-processing pass.

~/.config/doom/workflow/phases/phase6_deduplication.py
"""
from __future__ import annotations

import re


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

## `phase7_audit.py`

**Path:** `~/.config/doom/workflow/phases/phase7_audit.py`

````python
"""Phase 7: Comprehensive Audit.

Validate the final `TranslatedConfig` against the doomemacs source tree:
- Tangle headers are correct
- Doom macros are real (not hallucinated)
- `(after! <package> ...)` uses feature symbols
- `:config literate` is in the dooM! block
- No duplicate setqs
- Elisp is paren-balanced

~/.config/doom/workflow/phases/phase7_audit.py
"""
from __future__ import annotations

import re

from loguru import logger

from agents import AUDIT_AGENT
from models import AuditFinding, AuditReport, Severity
from state import DoomStitcherState
from utils.elisp import (
    balanced_parens_check,
    extract_doom_macro_uses,
    iter_forms,
)


# Known Doom macros (defined in doomemacs/core/core-lib.el or lisp/doom-lib.el)
KNOWN_DOOM_MACROS = {
    "after!", "use-package!", "use-package-hook!", "setq-hook!", "setq!",
    "add-hook!", "remove-hook!", "def-hydra!", "defun!", "defmacro!",
    "map!", "appendq!", "prependq!",
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
    # `:config` and `literate` may be on the same line (":config literate")
    # or on separate lines, as phase4's deterministic injection and most
    # hand-written `doom!` blocks format one module per line:
    #   (doom! :config
    #          literate
    #          ...)
    if not re.search(r":config\s+literate\b", doom_block, re.DOTALL):
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
````

## `phase7_hints.xml`

**Path:** `~/.config/doom/workflow/prompts/phase7_hints.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<directive id="phase7-audit" version="1.0" format="markdown">
  <metadata>
    <title>Phase 7 — Audit — Additional Context</title>
    <phase>7</phase>
  </metadata>
  <content><![CDATA[
## Phase 7 — Audit — Additional Context

Verification checklist (each item must pass before approving the output):

- [ ] Every `package!` exists in Doom's pinned package list (or is declared as a `:recipe` or `:pin` in `packages.el`).
- [ ] Every macro used (`after!`, `use-package!`, `map!`, `setq-hook!`, `add-hook!`, `def-hydra!`, `package!`) is a real Doom macro defined in `doomemacs/core/core-lib.el` or `lisp/doom-lib.el`.
- [ ] All `(after! <feature> ...)` blocks reference a feature symbol, NOT a major mode name. Common mistake: `(after! python-mode ...)` — correct: `(after! python ...)`.
- [ ] Tangle headers are valid: every `#+begin_src` is matched by `#+end_src`; `:tangle` paths resolve to `config.el`, `init.el`, or `packages.el` relative to `~/.config/doom/`.
- [ ] No vanilla `use-package` without the bang (unless wrapping a third-party lib that requires it).
- [ ] `(doom! :config literate ...)` is present in the `init.el` source block.
- [ ] `load-path` update for `lisp/` is present and correct.
- [ ] `(require 'org-src-context)` is wrapped in `(after! org ...)`.
- [ ] No `setq` duplicates Doom defaults (this is enforced by Phase 6 but the auditor should re-check).
]]></content>
</directive>
```

## `phase8_output_generation.py`

**Path:** `~/.config/doom/workflow/phases/phase8_output_generation.py`

```python
"""Phase 8: Output Generation.

Render the final ``config.org``, ``README.md``, ``.gitignore``, and
``setup-doom.sh``. Perform filesystem operations:
  - Move ``lisp/org-src-context.el`` from ``emacs/lisp/`` to ``lisp/``
  - Delete the ``emacs/`` directory

The static output templates (README, .gitignore, setup-doom.sh) are stored
as plain files in ``workflow/templates/`` and read here. This avoids the
syntax hazards of embedding markdown in Python source: the README
contains triple-backtick fenced code blocks that would terminate a
Python triple-quoted string early.

~/.config/doom/workflow/phases/phase8_output_generation.py
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

# ---------- Template directory & lazy loaders -----------------------------
# ``Path(__file__).resolve().parent`` is ``workflow/phases/``; templates
# live one level up at ``workflow/templates/``.
_TEMPLATES_DIR: Path = Path(__file__).resolve().parent.parent / "templates"


def _read_template(filename: str) -> str:
    """Read a static output template verbatim."""
    path = _TEMPLATES_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Template file not found: {path}")
    return path.read_text(encoding="utf-8")


# ---------- Phase entry point ---------------------------------------------


def phase8_output_generation(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P8] Generating outputs..."]
    deduped = state.get("deduplicated_config")
    audit_report = state.get("audit_report")

    if deduped is None:
        msg = "Phase 8: no deduplicated_config from prior phases"
        return {"errors": [msg], "log_lines": log}

    # If the audit failed with errors, refuse to write to avoid corrupting
    # the user's config. They can fix the vanilla input and re-run.
    if audit_report and not audit_report.passed:
        err_count = sum(
            1 for f in audit_report.findings if f.severity == Severity.ERROR
        )
        msg = f"Refusing to write outputs: {err_count} audit errors remain. See audit_report."
        logger.error(msg)
        return {"errors": [msg], "log_lines": log}

    # ---- Build the dynamic config.org content (LLM-generated upstream) --
    config_el_parts: list[str] = []
    if deduped.config_el.load_path_setup:
        config_el_parts.append(deduped.config_el.load_path_setup)
    if deduped.config_el.after_org_setup:
        config_el_parts.append(deduped.config_el.after_org_setup)
    config_el_parts.extend(deduped.config_el.config_forms)
    if deduped.config_el.transient_defs:
        config_el_parts.append(
            "\n;;; Transients\n" + "\n".join(deduped.config_el.transient_defs)
        )
    if deduped.config_el.custom_defs:
        config_el_parts.append(
            "\n;;; Custom Defs\n"
            + "\n".join(d.body for d in deduped.config_el.custom_defs)
        )
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

    # ---- Static templates loaded verbatim from workflow/templates/ ------
    readme_text = _read_template("README.md")
    gitignore_text = _read_template(".gitignore")
    setup_doom_text = _read_template("setup-doom.sh")

    # ---- Filesystem operations (idempotent, with backups) ---------------
    files_written: list[str] = []
    root = config.CONFIG.paths.doomdir

    targets: list[tuple[Path, str]] = [
        (root / "config.org", config_org_text),
        (root / "README.md", readme_text),
        (root / ".gitignore", gitignore_text),
        (root / "setup-doom.sh", setup_doom_text),
    ]
    for path, content in targets:
        if config.CONFIG.dry_run:
            log.append(f"[P8] DRY-RUN: would write {path} ({len(content)} bytes)")
            continue
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
    if setup_doom.is_file() and not config.CONFIG.dry_run:
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
        "final_readme": readme_text,
        "final_gitignore": gitignore_text,
        "final_setup_doom": setup_doom_text,
        "final_files_written": files_written,
        "log_lines": log,
        "phase_status": {"phase8_output_generation": "completed"},
    }
```

## `phase9_maintenance.py`

**Path:** `~/.config/doom/workflow/phases/phase9_maintenance.py`

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
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return None


def _config_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def phase9_maintenance(state: DoomStitcherState) -> dict:
    log: list[str] = ["[P9] Building maintenance summary..."]

    if config.CONFIG.skip_maintenance:
        log.append("[P9] Skipped (DOOM_STITCHER_SKIP_MAINTENANCE=1)")
        return {
            "maintenance_summary": None,
            "log_lines": log,
            "phase_status": {"phase9_maintenance": "skipped"},
        }

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
    out_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, default=str)
    )
    log.append(f"[P9] Wrote {out_path}")

    return {
        "maintenance_summary": summary,
        "log_lines": log,
        "phase_status": {"phase9_maintenance": "completed"},
    }

```

## `prompt.py`

**Path:** `~/.config/doom/workflow/prompt.py`

```python
"""Doom-Stitcher runtime directive loader.

The actual prompt content lives in XML files under workflow/prompts/.
This module:
  1. Locates the prompts directory relative to this file.
  2. Parses each ``<directive>`` XML file (CDATA-wrapped markdown).
  3. Exposes module-level constants that other modules import.
  4. Caches the loaded content (loaded once at import time).

Storing the prompts as XML files (rather than Python triple-quoted strings) eliminates the syntax hazards of embedding markdown — with its triple backticks, escaped backslashes, f-string braces, and embedded code samples — directly in source code. It also keeps the prompt engineering content out of version-control diffs for the application logic.

~/.config/doom/workflow/prompt.py
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

# Resolved once at import time. ``Path(__file__).resolve().parent`` is the
# workflow/ directory; the prompts live in workflow/prompts/.
_PROMPTS_DIR: Path = Path(__file__).resolve().parent / "prompts"


@lru_cache(maxsize=8)
def _load_xml_directive(filename: str) -> str:
    """Load a ``<directive>`` XML file and return its ``<content>`` CDATA text.

    The XML structure is::

        <directive id="..." version="...">
            <metadata>...</metadata>
            <content><![CDATA[...markdown body...]]></content>
        </directive>

    The CDATA wrapper preserves triple backticks, ampersands, and angle
    brackets verbatim — none of which would survive as a Python string
    literal without escape-hell.
    """
    path = _PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    content_elem = root.find("content")
    if content_elem is None or content_elem.text is None:
        raise ValueError(f"Prompt file {path} has no <content> element or empty body")
    return content_elem.text.strip()


# ---------- Public constants -----------------------------------------------
# These are imported by ``agents.py`` and concatenated with the base
# directive for per-phase agent factory functions. Loaded once, cached.

DOOM_STITCHER_DIRECTIVE: str = _load_xml_directive("directive.xml")
PHASE_4_HINTS: str = _load_xml_directive("phase4_hints.xml")
PHASE_5_HINTS: str = _load_xml_directive("phase5_hints.xml")
PHASE_7_HINTS: str = _load_xml_directive("phase7_hints.xml")


def get_prompts_dir() -> Path:
    """Return the prompts directory (useful for diagnostics / `--debug`)."""
    return _PROMPTS_DIR
```

## `README.md`

**Path:** `~/.config/doom/workflow/templates/README.md`

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
- **Nix with flakes enabled** + a `.env.keys` file (dotenvx private key) in
  the repo root -- only needed if you plan to re-run the `doom-stitcher`
  workflow (see "Regenerating the Literate Config" below)

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

| Task                                 | Command                                     |
| ------------------------------------ | ------------------------------------------- |
| Re-tangle after editing `config.org` | `~/.config/emacs/bin/doom sync`             |
| Reload config (in Emacs)             | `M-x doom/reload` or `SPC h r r`            |
| Update all packages                  | `~/.config/emacs/bin/doom upgrade`          |
| Find a config heading                | `SPC h f` (with `:config literate` enabled) |
| Check for issues                     | `~/.config/emacs/bin/doom doctor`           |

## Repository Layout

```
.
├── config.org           ← EDIT THIS (literate source)
├── init.el              ← GENERATED, do not edit
├── config.el            ← GENERATED, do not edit
├── packages.el           ← GENERATED, do not edit
├── lisp/                ← Custom Elisp
│   └── org-src-context.el
├── doomemacs/           ← Doom source tree (read-only reference)
├── workflow/            ← doom-stitcher agentic pipeline
├── flake.nix            ← Nix dev shell + `nix run` entry points
├── process-compose.yml  ← orchestrates redis + litellm + workflow
├── litellm-config.yaml  ← LiteLLM proxy: model pools, caching, auth
├── .env                 ← dotenvx-encrypted secrets (safe to commit)
├── .env.keys            ← dotenvx private key, NOT committed (gitignored)
└── setup-doom.sh        ← First-time install script
```

## Regenerating the Literate Config

If you pull upstream changes to your vanilla config or want to re-derive the
Doom config from scratch:

```bash
# Restore vanilla sources under emacs/
mkdir -p emacs/lisp
# ... drop your vanilla config.org, early-init.el, lisp/org-src-context.el here

# From the repo root (where flake.nix, .env, and .env.keys live):
nix run            # starts redis + litellm + the workflow together
# -- or, if a LiteLLM proxy is already running on $OPENAI_BASE_URL --
nix run .#workflow
```

Both entry points decrypt `.env` via `dotenvx` before launching anything, so
`.env.keys` (or `$DOTENV_PRIVATE_KEY`) must be present.

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
the `*Org Babel Output*` buffer.

**Want to start over?**

```bash
rm config.el init.el packages.el
~/.config/emacs/bin/doom sync
```
````

## `setup-doom.sh`

**Path:** `~/.config/doom/workflow/templates/setup-doom.sh`

```bash
#!/bin/bash
echo "(doom! :config literate)" >~/.config/doom/init.el
git clone --depth 1 https://github.com/doomemacs/doomemacs ~/.config/emacs
~/.config/emacs/bin/doom install
~/.config/emacs/bin/doom sync
```

## `.gitignore`

**Path:** `~/.config/doom/workflow/templates/.gitignore`

```gitignore
# ── Doom / Emacs ────────────────────────────────────────────────────────
.local/
*.elc
auto-save-list/
*~
\#*\#

# ── doom-stitcher workflow ─────────────────────────────────────────────
workflow/.state/
workflow/__pycache__/
workflow/**/__pycache__/
*.bak

# ── Secrets ───────────────────────────────────────────────────────────
# .env is dotenvx-encrypted and safe to commit, but its private key
# (.env.keys, or a local DOTENV_PRIVATE_KEY export) must never be.
.env.keys
.env.keys.*
.env*.local
```

## `state.py`

**Path:** `~/.config/doom/workflow/state.py`

```python
"""LangGraph state definition for the doom-stitcher DAG.

The state is a TypedDict with Annotated fields for accumulators (errors, messages). Each phase reads from and writes to a designated slice; the graph's add_node functions are pure (modulo LLM calls) and return partial state updates.

~/.config/doom/workflow/state.py
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


def add_or_update(
    current: dict[str, str] | None, new: dict[str, str] | None
) -> dict[str, str]:
    """Reducer: merge `new` into `current` with new values winning."""
    base = dict(current or {})
    base.update(new or {})
    return base
```

## `tools.py`

**Path:** `~/.config/doom/workflow/tools.py`

```python
"""Tools exposed to Pydantic AI agents.

These are *deterministic* I/O functions. They are the only way the agents
can read source files; this keeps the LLM from hallucinating file
contents and makes the workflow auditable.

~/.config/doom/workflow/tools.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


import config
from utils.elisp import (
    balanced_parens_check,
    extract_doom_macro_uses,
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
                    "path": str(
                        mod_dir.relative_to(config.CONFIG.paths.doomemacs_subdir)
                    ),
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


def search_doom_modules(
    pattern: str, file_glob: str = "*.el", max_results: int = 20
) -> list[dict[str, str]]:
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
                        "path": str(
                            path.relative_to(config.CONFIG.paths.doomemacs_subdir)
                        ),
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

## flake.nix

**Path:** `~/.config/doom/flake.nix`

```nix
{
  description = "doom-stitcher: vanilla Emacs → literate Doom Emacs translator (Nix-managed, Python 3.13 + PGO + LTO)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python313.override {
          enableOptimizations = true;
          enableLTO = true;
          reproducibleBuild = false;
        };

        workflowDeps = python.withPackages (ps: with ps; [
          pydantic
          pydantic-ai-slim
          langgraph
          langchain-core
          openai
          httpx
          pyyaml
          rich
          tenacity
          loguru
          platformdirs
          litellm
        ]);

        # dotenvx is not packaged in nixpkgs as of this writing, so we pin
        # and shim it via `npx`. This is the *only* thing that touches
        # `.env`: it decrypts the dotenvx-encrypted secrets (using
        # `.env.keys` / $DOTENV_PRIVATE_KEY, which must exist alongside
        # `.env` but is intentionally NOT part of this flake) and injects
        # the plaintext values into the environment of whatever command it
        # wraps. Every app below runs through this wrapper so LITELLM_*,
        # GOOG_*, REDIS_*, DOOM_STITCHER_MODEL_*, DOOMDIR, etc. are all
        # available -- nothing else in this repo parses `.env` itself.
        dotenvx = pkgs.writeShellScriptBin "dotenvx" ''
          exec ${pkgs.nodejs_22}/bin/npx --yes @dotenvx/dotenvx@1.71.2 "$@"
        '';

        # Shared initialization logic between devShell and running apps.
        # Guarantees identical paths and configurations everywhere.
        shellInit = ''
          export DOOMDIR="''${DOOMDIR:-$PWD}"
          export WORKFLOW_DIR="$DOOMDIR/workflow"
          export PYTHONUNBUFFERED=1
          export PYTHONPATH="$WORKFLOW_DIR''${PYTHONPATH:+:$PYTHONPATH}"
          export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
        '';

      in {
        # ════════════════════════════════════════════════════════════════════
        # DEVELOPMENT ENVIRONMENT (nix develop)
        # ════════════════════════════════════════════════════════════════════
        devShells.default = pkgs.mkShell {
          name = "doom-stitcher";

          packages = [
            workflowDeps
            dotenvx
            pkgs.process-compose
            pkgs.cacert
            pkgs.redis
            pkgs.pyrefly
            pkgs.ruff
          ];

          shellHook = ''
            # Inject standardized environment variables
            ${shellInit}

            # Minimal startup sanity checks
            echo "===================================================================="
            echo "⚡ Entering development environment for doom-stitcher ⚡"
            echo "===================================================================="
            echo "🔍 Environment verification:"
            echo "    Python:       $(python --version 2>&1)"

            # Fetch compiler flag metadata precisely matching user flags
            PGO_STATUS=$(python -c "import sysconfig; print('-fprofile-use' in (sysconfig.get_config_var('PY_CFLAGS') + sysconfig.get_config_var('PY_CFLAGS_NODIST')))")
            LTO_STATUS=$(python -c "import sysconfig; print('-flto' in (sysconfig.get_config_var('PY_CFLAGS') + sysconfig.get_config_var('PY_CFLAGS_NODIST')))")

            echo "    PGO Flag Check: $PGO_STATUS"
            echo "    LTO Flag Check: $LTO_STATUS"
            echo "--------------------------------------------------------------------"
            if [ ! -f "$DOOMDIR/.env.keys" ] && [ -z "''${DOTENV_PRIVATE_KEY:-}" ]; then
              echo "⚠️  No $DOOMDIR/.env.keys and \$DOTENV_PRIVATE_KEY is unset."
              echo "    'nix run' will fail to decrypt .env until you add one."
            fi
            echo "💡 Run 'nix run' to start the entire process-compose pipeline."
            echo "💡 Run 'nix run .#workflow' to only invoke the Python script."
            echo "💡 Run 'nix run .#litellm' to only run the LiteLLM server."
            echo "💡 For an ad-hoc shell with secrets decrypted: dotenvx run -f \"\$DOOMDIR/.env\" -- \$SHELL"
            echo "===================================================================="
          '';
        };

        # ════════════════════════════════════════════════════════════════════
        # RUNNABLE APPLICATIONS (nix run)
        # ════════════════════════════════════════════════════════════════════

        # Default: start LiteLLM + workflow together
        apps.default = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher";
            runtimeInputs = [ pkgs.process-compose pkgs.cacert dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}
              # --disable-dotenv: process-compose must NOT also load
              # $DOOMDIR/.env itself -- that file is dotenvx-encrypted
              # ciphertext, and process-compose's own .env loading would
              # inject the literal "encrypted:..." strings, clobbering the
              # plaintext values dotenvx just injected below.
              exec dotenvx run -f "$DOOMDIR/.env" -- \
                process-compose -f "$DOOMDIR/process-compose.yml" --disable-dotenv --tui=false up
            '';
          });
        };

        # Just the workflow (assumes LiteLLM already serving on $OPENAI_BASE_URL)
        apps.workflow = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher-workflow";
            runtimeInputs = [ workflowDeps pkgs.cacert pkgs.curl dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}

              # This app assumes a LiteLLM proxy is ALREADY running on
              # $OPENAI_BASE_URL (defaults to http://localhost:4000, same
              # default as workflow/config.py). Check that first so a
              # missing proxy fails with a clear message instead of a
              # raw connection-refused traceback from main.py.
              litellm_url="''${OPENAI_BASE_URL:-http://localhost:4000}"
              if ! curl -fsS --max-time 2 "$litellm_url/health/liveliness" >/dev/null 2>&1; then
                echo "error: no LiteLLM proxy reachable at $litellm_url" >&2
                echo "  Start one first, e.g. in another terminal: nix run .#litellm" >&2
                echo "  ...or run the full stack instead:           nix run" >&2
                exit 1
              fi

              cd "$WORKFLOW_DIR"
              exec dotenvx run -f "$DOOMDIR/.env" -- python main.py "$@"
            '';
          });
        };

        # Just the LiteLLM proxy
        apps.litellm = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher-litellm";
            runtimeInputs = [ workflowDeps pkgs.cacert dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}
              exec dotenvx run -f "$DOOMDIR/.env" -- \
                litellm \
                --config "$DOOMDIR/litellm-config.yaml" \
                --port "''${LITELLM_PORT:-4000}" \
                "$@"
            '';
          });
        };
      }
    );
}
```

## process-compose.yml

```yaml
# ~/.config/doom/process-compose.yml
version: "0.5"

settings:
  log_level: info

processes:
  redis:
    command: "redis-server --port \"${REDIS_PORT}\" --requirepass \"${REDIS_PASSWORD}\""
    readiness_probe:
      exec:
        command: "redis-cli -p \"${REDIS_PORT}\" -a \"${REDIS_PASSWORD}\" --no-auth-warning ping"
      interval: 1s
      timeout: 1s
      retries: 15
      start_period: 2s
    availability:
      restart: on_failure
      max_restarts: 5
      backoff: 1s
    shutdown:
      signal: 15 # SIGTERM, cleanly flush memory to disk if snapshotting
      timeout_seconds: 5

  litellm:
    command: "litellm --config ${DOOMDIR}/litellm-config.yaml --port 4000"
    depends_on:
      redis:
        condition: process_healthy # Wait for Redis to respond to ping first
    readiness_probe:
      http_get:
        host: 127.0.0.1
        port: 4000
        path: /health/liveliness
        scheme: http
      interval: 2s
      timeout: 2s
      retries: 30
      start_period: 10s
    availability:
      restart: on_failure
      max_restarts: 3
      backoff: 2s
    shutdown:
      signal: 15 # SIGTERM, let LiteLLM flush in-flight reqs
      timeout_seconds: 10
    environment:
      - "HOME=${HOME}"
      - "LITELLM_LOG=INFO"
      - "LITELLM_TELEMETRY=False"

  workflow:
    command: "python main.py"
    working_dir: "${WORKFLOW_DIR}"
    depends_on:
      litellm:
        condition: process_healthy # Wait until /health/liveliness returns 200
    availability:
      restart: on_failure
      max_restarts: 1
      exit_on_end: true # Tear everything down when workflow exits
    shutdown:
      signal: 15
      timeout_seconds: 30
    environment:
      - "PYTHONUNBUFFERED=1"
      - "DOOMDIR=${DOOMDIR}"
      - "OPENAI_BASE_URL=http://localhost:4000"
```

## litellm-config.yaml

**Path:** `~/.config/doom/litellm-config.yaml`

```yaml
model_list:
  # Each `model_name` below is a model *group* that LiteLLM load-balances
  # (simple-shuffle) across multiple Google AI Studio accounts, multiplying
  # the effective free-tier quota for that role. Group names match the
  # DOOM_STITCHER_MODEL_* aliases that workflow/config.py resolves by
  # default (see config.py's ModelConfig), so the workflow authenticates
  # and routes correctly out-of-the-box even if those env vars are never
  # set in `.env`. Set DOOM_STITCHER_MODEL_DEFAULT / _TRANSLATION / _AUDIT /
  # _EXTRACTION in `.env` only if you want a phase to use a different
  # group/model than its default.

  # -- doom-stitcher-default (phases 1-3: extraction) ----------------------
  - model_name: "doom-stitcher-default"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_1"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-default"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_2"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-default"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_3"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  # -- doom-stitcher-translator (phases 4-6: translation/refinement/dedup) --
  - model_name: "doom-stitcher-translator"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_4"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-translator"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_5"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-translator"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_6"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  # -- doom-stitcher-auditor (phase 7: comprehensive audit) -----------------
  - model_name: "doom-stitcher-auditor"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_7"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-auditor"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_8"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

  - model_name: "doom-stitcher-auditor"
    litellm_params:
      model: "gemini/gemini-3.5-flash"
      api_key: "os.environ/GOOG_9"
      stream: true
      reasoning_effort: "high"
    model_info:
      supports_reasoning: true

# ── Router settings ────────────────────────────────────────────────────────
router_settings:
  routing_strategy: "simple-shuffle"
  num_retries: 3
  retry_after: 10
  allowed_fails: 3
  cooldown_time: 60

# ── Global LiteLLM settings ────────────────────────────────────────────────
litellm_settings:
  drop_params: true
  request_timeout: 120
  cache: true
  # Back the response cache with the Redis instance already provisioned in
  # process-compose.yml, so repeated identical prompts (common across
  # phases 3 and 7 when re-querying the same Doom module defaults) don't
  # burn additional free-tier quota.
  cache_params:
    type: "redis"
    host: "os.environ/REDIS_HOST"
    port: "os.environ/REDIS_PORT"
    password: "os.environ/REDIS_PASSWORD"
    ttl: 3600

# ── Proxy general settings ─────────────────────────────────────────────────
general_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"
```

## .env (encrypted)

```txt
#/-------------------[DOTENV_PUBLIC_KEY]--------------------/
#/            public-key encryption for .env files          /
#/       [how it works](https://dotenvx.com/encryption)     /
#/----------------------------------------------------------/
DOTENV_PUBLIC_KEY="0327ce278e5aeaf561fc5871ec5c769e8f1b5702993b561d354254d95798d74e76"

# .env
# ── 🗝️ LiteLLM Proxy Access Keys ──────────────────────────────────────
LITELLM_MASTER_KEY=encrypted:BA8dswVHEqJZK6LaJLwgpX5AWZ292aHfQfN+z1ea2cIXi4AkI/StWO7ot5jxBTLOvfD3Qz4sosvLQWv6zcxR3uleYfbl3IP64gb3c4tdH/boUJLr/Qr9O5KThtK81RGD48orCjQ8Q9iw76pA7Da4qBiDy0VKt9w9vjmqGfWgzklos8w/exSDLNTnu8ZHUM/4SHKxIQFaPuot7EFKDrCBioc=

# ── 🤖 Google Gemini API Load-Balancer Pool ──────────────────────────
# Distributes weight equally across your simple-shuffle routing list
GOOG_1="encrypted:BOOqWrMa68dY3V869HFZA7nWjJSn4E5n1R3diregqMcgcwKs4B6aYh7y8U8ov1iWWRMfOnd+3wBORijRYIub1r0SGOcM/nQaRgGbpOcmN+73Hx5hhHhB+UoHqAA0GPMbHXmUWZcUkaX6LIxFHNg4AgHHKqWvx0v5tsZvs5DCMYraeq8LbbPKheJ7LZa77s6tHB/Eb3wT"
GOOG_2="encrypted:BOMVtwcveVxLNsxvdsw/pNUvzbgzeV2jsb/PgSVFvRk4tikqZiI55LYR7gBV2KoR96iNCqouOsF6EHcxObzSuLuqR9mdaAhVKoFV05kKn+wF1UWT5jX6wbJV9rWQ1hJhIiQc+ekAmlVnrq2gwOUvhzPEzLJ+OOEcg6iDuB2GdBFmmmtpzivjbc/j9SQMDmcCE6aU6YMn"
GOOG_3="encrypted:BGKWb8qFUADbx6ZMIhaW98snBzFtgkqvKcf4KX9+rCBlyMcgJhPcCzIdu+RVh8SlsFpQS7tfd6SrTz4cIXPpmEeNwFJbFide7Gf/wJ5JpPUipI8HpdBr0bK5R1mV91NpHi6u19x0iUqobkoG9QcgPvC7FvEcDRRuIAS0R8pDlgCmAu8qufDA72V0INydwckoD8b6rLZW"
GOOG_4="encrypted:BKoTx2rSg6AVW4CTlGp/w49UBMOsovv3HhFKLC+p+78LDQejnPx9Y7qB1a5g0ZIEgPL3jSL8TBIjFicgfks0MqPiJrsrhyghe1iEvoec2KqJz8ie3NrScSNFQWoAb6Il5eRPss8zzE/q4nYUL1Qwqr4FnYH8hBkQgckahB54Rns6qIZvGIkTbEH+b0YHW/oxS7ahsXqO"
GOOG_5="encrypted:BFLEnANsYg6yoZtNlCiA0VYxmfLXa4CW1lWprCKz7sS/95i5L0V2CZE+mfwWUohlx8Q85l1N6IfrN9hBMV3qHDRYGiv3JyTVaZb54hWNjt2muiA9809p23e0a0GaayIieWr2RX4E+42G06J6hGxNRYxAGYMaVQm6WKX4/GJPi6Agz2/bgxgkkgGvMn2WNpZCCduMSV6n"
GOOG_6="encrypted:BLx4XpFtHzwgQK6WFWcY6t90SCRJxuw6E9NLPFjSTXCmlZkxUktPNxPZKPYgdIXS5Jm9ozwKfD3wLsZ8JzSMU4IszL0QIHhQtfjFX1CKpvvEESd95TZAz4v1zSsaRgHgN2NOKDmfGjw3zr5QEgBPY/tjv8XyG194dw5hadgPkX2i9ro7LbsCAL7Uh9M/q+AFk2nD312h"
GOOG_7="encrypted:BFtLgBVrLWHcBd0MBeCJ7g7ek1H9LN703+RV0HB+Z3/Tt4bexI5WkX+bAZhvKHO8rr9pTK9vj5ocI9+n+MtIeup7Jc/uLwPA8g+PWZbu3uRCbe74v1d+Ym4zbhiiQpylJjrdKqIyeX+E31yy7IOIlME0t30tBCT1zbYtVupNnXrlw0Fg0te3ACwnTbnauSTuSf0K8/pL"
GOOG_8="encrypted:BOYzA9+xSq5AcPUBGY5mStJZeAfXCneG5sJBvSvFOJR6/1yvnOsk+a+prsNkZznNN576favcGDz4e8MLPHRNmlt6iezSRV8tSk05C/P8KDTYWLdo+UmqKM7mJR2cKfIjap1R/jqv7/PZPwtM3P3CyMlh4cUFfJp0kA0Gq8Ti8E2LMASn9J9XAFBniOzZ1wZ3E04setvr"
GOOG_9="encrypted:BEiGBlIZpofwLEZwJJGAi4JCzAjXufLmpOgrgcHNrVqHOCHnQRO0BZEDU5Sjvi/Uk8KCv1DEpszUXwxEZkDAv3N+Cu3VziMu69cnfvysDrXxnuofIK5y+XZDTckk1KHPWBkuFg3t6iVhDpBIT6SQeMNtv7lyZOyvpWdfk/fCBJpbrXuPhu1b5owo5Ct20hyzWswiTQLz"

# ── 💾 Redis Cache Connectivity Settings ──────────────────────────────
# Matches the automated port metrics loaded inside your Nix network
REDIS_HOST="encrypted:BInMbBykegNJpVTNwDKKLQZyy3Um0llEEnYDrbm21wUrpTy9nu+EWKr5XBWmjtRslmXcpmNCugp2B2WNBDdue5MwB+wNgMEfrTCSB7XvMo9Bc+VlnHkSPGJlI/jMvRw69HXcAw7+sIDXuw=="
REDIS_PORT="encrypted:BCWungUJeY07Jz6btneZ9TWfcJZQKYGjzeh/WGiNwRinGrSud5oXsRuyP2uHJgMNKXYSBc9sp8FGY/+TMpTh3rU+uNXJ7f7axni2efgTzW90JlpnbOhRQgubBg4ViQ3NwilqgQA="
REDIS_PASSWORD="encrypted:BCYw9EHeVHlFJz3d5evi4BcSbJaZZaJWgGndhfjbuaQx5qtOop/vaJIxWFjZ8HQWj84aLpQ8M/S/MndeUHuq4bfF0JmlLtDgof7Yg3H5j44bdQPVeDaXgLZcn4SuvB3USw=="

# ── 🧭 Project System Core Paths ──────────────────────────────────────
# Keeps paths synchronized if you execute code outside of the root folder
DOOMDIR="encrypted:BK5Ns/MzjEMx1fRvJj2y38F6zzvbAbXy73CBdiAqEAbnX4yZOjlH9M1lR+BldCxQsCLCQNz/4KYEI6my6q5Pkwdy0lk5I7a9VlIe1mdy/pAk+1+Npa3u05ndlsLYEBwXEB8="
WORKFLOW_DIR="encrypted:BL+9vpiznyx0LCYPGYJdNRVxCSJM30BnJyp3PmnS8w93ZIm7e0K4yv7nDpDV44bUE2IlYaM49RyL/6ecpaGCgPJ5aN3rAzTBe+aG3GM82tOWF+r/imqfBGH2Sd9znT1ySpnSLTF7iejRJMo="

# ── 🧠 LangGraph Workflow Routing & Optimization ──────────────────────
# Custom routing targets mapping back to your LiteLLM config model pools
DOOM_STITCHER_MODEL_DEFAULT="encrypted:BNHH0rM9mdS9+Nf1DxrVLv8pJRo/IruGkK2J+0HcMk2khx1Pwb2cNDie0wTwtI5VYcHqSYMa9ZHpFhH3dun9OWJvgZu+I2C4icgWLLlDT8aYawCPJcDihtHI94Cl4PmAavK0IwW7Quw8oJzRC++SfVM="
DOOM_STITCHER_MODEL_TRANSLATION="encrypted:BKacvshxXMKXy04XRcXwSlOQ/PYuWZ6A9lvZIotNanJbo3HuxUaGcCiGnHpTO8XdU47hcrZMeusX6YX9wZcDxIDTA4CrDIenPqHkZ6DqA32YORcrv7o4gm759YaFR/KK5TQTqIlppkMkZxApbTaaEIg="
DOOM_STITCHER_MODEL_AUDIT="encrypted:BDZIcIFAlduuko6GxMtz372POLQABh+qh3t4cxFjLrtgdoL2UjMydMh/0jX2iYWiUKZu8nVf+ZxZmUqvbTVUpDWuYCP+fu7KuKN/FHwu9/+Vguc/59sWfRKu29jaTU53+efT1/7tnaSxutOaf11ZjC0="
DOOM_STITCHER_MODEL_EXTRACTION="encrypted:BKp2PKcCRgegLqAL2QZ6yTNUvjsR/ZL7puQ5aEaQOwXWkYhDjVdZn45gDc2/gVUHsZfl/mQpHP6QnfynwXYnQUKQi4BCUEZUhajC7yBpUXaBIw/olXEedZBI1ic+IQHqi/H5vgnCSa5VveTytmiJBDo="

# ── 🛠️ Debugging and Runtime Execution Flags ──────────────────────────
PYTHONUNBUFFERED="encrypted:BM4YF8HTT5SYYpBCge/pKpuCD1lTqQZ+YgYIho4RkQKK1kEyMJEohuV2cryQrCw2PcOXfC7p+j8pm3xmfT5KqmamGhzyaSO6xfAu8TNpNw0dV9bj/QL4/b4uL73Nh9KRFpU="
DOOM_STITCHER_VERBOSE="encrypted:BIETUT6LhaapKZBB8eBHdAG0fzTqXy/GqU4MD+VKV7y6DER+lZcd5D+czYbIAE3jy0R9a3Q/rM0ttpAQJhFTDWi1wuv0+nYmvCgRXQUbDuomKVR/iT3p9U42wEeKOZ4qkfI="
DOOM_STITCHER_DRY_RUN="encrypted:BMLapX72yi3ccp+7dF+KyO+UySgeOtZzM5jVJZRkXSJE8etWtjAUvkLcpc7BqbgpNpS5gt1rgNZoeENBItW4Ag47LPyw/rwbdYyRkDLn49stjM7L9XTsKudqqAIvXRjxytA="

```
