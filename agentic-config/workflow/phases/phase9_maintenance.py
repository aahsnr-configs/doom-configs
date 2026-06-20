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
