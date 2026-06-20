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
        head_match = re.match(
            r"\s*\((setq!?|setq-default|setq-hook!)\s+([^\s)]+)\s+(.+?)\)\s*$",
            stripped,
            re.DOTALL,
        )
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
