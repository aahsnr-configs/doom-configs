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
        # If doomdir is relative, resolve it relative to the parent of workflow_dir (the repo root)
        if not self.doomdir.is_absolute():
            abs_doomdir = (self.workflow_dir.parent / self.doomdir).resolve()
            object.__setattr__(self, "doomdir", abs_doomdir)

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
