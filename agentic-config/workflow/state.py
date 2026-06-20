"""LangGraph state definition for the doom-stitcher DAG.

The state is a TypedDict with Annotated fields for accumulators (errors, messages). Each phase reads from and writes to a designated slice; the graph's add_node functions are pure (modulo LLM calls) and return partial state updates.

~/.config/doom/workflow/state.py
"""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict

from models import (
    AuditReport,
    DoomModule,
    DoomModuleData,
    MaintenanceSummary,
    TranslatedConfig,
    UserInitConfig,
    VanillaConfig,
)


class DoomStitcherState(TypedDict, total=False):
    # --- Static config (set at graph entry) ----------------------------
    root_dir: str
    workflow_dir: str

    # --- Phase 1: vanilla ingestion -------------------------------------
    vanilla_config: VanillaConfig | None

    # --- Phase 2: user init.el ingestion --------------------------------
    user_init: UserInitConfig | None
    enabled_modules: list[DoomModule]

    # --- Phase 3: doom module ingestion ---------------------------------
    doom_module_data: dict[str, DoomModuleData]  # keyed by "category/name"

    # --- Phase 4: initial translation -----------------------------------
    translated_config: TranslatedConfig | None

    # --- Phase 5: refinement --------------------------------------------
    refined_config: TranslatedConfig | None

    # --- Phase 6: deduplication -----------------------------------------
    deduplicated_config: TranslatedConfig | None

    # --- Phase 7: audit --------------------------------------------------
    audit_report: AuditReport | None

    # --- Phase 8: output generation -------------------------------------
    final_config_org: str | None
    final_readme: str | None
    final_gitignore: str | None
    final_setup_doom: str | None
    final_files_written: list[str]

    # --- Phase 9: maintenance -------------------------------------------
    maintenance_summary: MaintenanceSummary | None

    # --- Accumulators (reducers) ----------------------------------------
    errors: Annotated[list[str], add]
    phase_status: Annotated[dict[str, str], add_or_update]
    log_lines: Annotated[list[str], add]


def add_or_update(
    current: dict[str, str] | None, new: dict[str, str] | None
) -> dict[str, str]:
    """Reducer: merge `new` into `current` with new values winning."""
    base = dict(current or {})
    base.update(new or {})
    return base
