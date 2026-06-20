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
