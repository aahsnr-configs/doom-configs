"""Phase node functions exposed to LangGraph.

Each phase is a pure (or near-pure) function: (state) -> partial_state_update. LLM calls happen via the shared agent instances in agents.py.

~/.config/doom/workflow/phases/__init__.py
"""
