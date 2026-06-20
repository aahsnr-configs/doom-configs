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
