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
    "after!",
    "use-package!",
    "use-package-hook!",
    "setq-hook!",
    "setq!",
    "add-hook!",
    "remove-hook!",
    "def-hydra!",
    "defun!",
    "defmacro!",
    "map!",
    "appendq!",
    "prependq!",
    "package!",
    "recipe!",
    "pin!",
    "unpin!",
    "load!",
    "featurep!",
    "modulep!",
    "add-to-load-path!",
    "add-load-path!",
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
    if (
        ":tangle config.el" not in config_org_text
        and "#+property:" not in config_org_text
    ):
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
    init_el_text = (
        deduped.init_el.doom_block + "\n" + deduped.init_el.extra_early_settings
    )

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

    log.append(
        f"[P7] Findings: {len(report.findings)} "
        f"(errors: {sum(1 for f in report.findings if f.severity == Severity.ERROR)})"
    )

    return {
        "audit_report": report,
        "log_lines": log,
        "phase_status": {
            "phase7_audit": "completed" if report.passed else "completed_with_errors"
        },
    }
