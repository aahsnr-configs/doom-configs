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
