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
                "(doom!",
                "(doom!\n  :config\n  literate",
                1,
            )
        log.append(
            f"[P4] Produced translated_config: "
            f"{len(translated.packages_el.package_declarations)} packages, "
            f"{len(translated.config_el.config_forms)} config forms"
        )
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
