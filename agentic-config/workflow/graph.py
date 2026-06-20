"""LangGraph assembly: wires the 9 phases into a StateGraph.

The graph is a linear pipeline (P1 → P2 → ... → P9). P7 (audit) always
flows into P8 (output generation); P8 itself is the audit gate -- if
`audit_report.passed` is False, P8 logs the audit errors and refuses to
write any files, but the graph still continues to P9 so a maintenance
summary is produced for the (unwritten) run.

~/.config/doom/workflow/graph.py
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from phases.phase9_maintenance import phase9_maintenance

from phases.phase1_vanilla_ingestion import phase1_vanilla_ingestion
from phases.phase2_init_ingestion import phase2_init_ingestion
from phases.phase3_doom_ingestion import phase3_doom_ingestion
from phases.phase4_initial_translation import phase4_initial_translation
from phases.phase5_refinement import phase5_refinement
from phases.phase6_deduplication import phase6_deduplication
from phases.phase7_audit import phase7_audit
from phases.phase8_output_generation import phase8_output_generation
from state import DoomStitcherState


def build_graph():
    builder = StateGraph(DoomStitcherState)

    builder.add_node("phase1_vanilla_ingestion", phase1_vanilla_ingestion)
    builder.add_node("phase2_init_ingestion", phase2_init_ingestion)
    builder.add_node("phase3_doom_ingestion", phase3_doom_ingestion)
    builder.add_node("phase4_initial_translation", phase4_initial_translation)
    builder.add_node("phase5_refinement", phase5_refinement)
    builder.add_node("phase6_deduplication", phase6_deduplication)
    builder.add_node("phase7_audit", phase7_audit)
    builder.add_node("phase8_output_generation", phase8_output_generation)
    builder.add_node("phase9_maintenance", phase9_maintenance)

    builder.add_edge(START, "phase1_vanilla_ingestion")
    builder.add_edge("phase1_vanilla_ingestion", "phase2_init_ingestion")
    builder.add_edge("phase2_init_ingestion", "phase3_doom_ingestion")
    builder.add_edge("phase3_doom_ingestion", "phase4_initial_translation")
    builder.add_edge("phase4_initial_translation", "phase5_refinement")
    builder.add_edge("phase5_refinement", "phase6_deduplication")
    builder.add_edge("phase6_deduplication", "phase7_audit")
    builder.add_edge("phase7_audit", "phase8_output_generation")
    builder.add_edge("phase8_output_generation", "phase9_maintenance")
    builder.add_edge("phase9_maintenance", END)

    return builder.compile()


# The compiled graph is created at module load so main.py can stream it.
GRAPH = build_graph()
