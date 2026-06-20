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
    log.append(
        f"[P2] Detected {len(modules)} modules: "
        + ", ".join(f"{m.path}" for m in modules)
    )

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
        logger.warning(
            f"Phase 2 LLM cross-check failed: {e}; using deterministic parse"
        )
        user_init = UserInitConfig(
            modules=modules, raw_doom_block=full, source_path=str(init_path)
        )

    log.append(f"[P2] Final: {len(user_init.modules)} modules enabled")
    return {
        "user_init": user_init,
        "enabled_modules": [m for m in user_init.modules],
        "log_lines": log,
        "phase_status": {"phase2_init_ingestion": "completed"},
    }
