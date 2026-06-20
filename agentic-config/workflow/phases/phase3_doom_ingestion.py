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
                    log.append(
                        f"[P3]   {path}: {len(mod.files)} files, "
                        f"{len(mod.defaults)} defaults, {len(mod.packages)} packages"
                    )
            except Exception as e:
                logger.exception(f"Failed to process module {path}")
                log.append(f"[P3]   {path}: FAILED ({e})")

    return {
        "doom_module_data": doom_data,
        "log_lines": log,
        "phase_status": {"phase3_doom_ingestion": "completed"},
    }
