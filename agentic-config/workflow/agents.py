"""Pydantic AI agent factories.

Each agent is a stateless runner constructed from the runtime config. We use OpenAIChatModel + OpenAIProvider so the LiteLLM proxy is the sole model endpoint. The model_name strings are aliases defined in the user's litellm-config.yaml.

~/.config/doom/workflow/agents.py
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import config
from models import (
    AuditReport,
    DoomModuleData,
    TranslatedConfig,
    UserInitConfig,
    VanillaConfig,
)
from prompt import (
    DOOM_STITCHER_DIRECTIVE,
    PHASE_4_HINTS,
    PHASE_5_HINTS,
    PHASE_7_HINTS,
)
from tools import get_agent_tools

# ---------- Model provider factory ---------------------------------------


def _make_model(model_alias: str) -> OpenAIChatModel:
    """Build an OpenAIChatModel pointed at the local LiteLLM proxy."""
    provider = OpenAIProvider(
        base_url=config.CONFIG.models.base_url,
        api_key=config.CONFIG.models.api_key,
    )
    return OpenAIChatModel(model_alias, provider=provider)


# ---------- Agent factories ----------------------------------------------


def make_vanilla_ingestion_agent() -> Agent[None, VanillaConfig]:
    """Phase 1 agent: extract packages, keybindings, custom defs."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=VanillaConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=3,
    )


def make_user_init_ingestion_agent() -> Agent[None, UserInitConfig]:
    """Phase 2 agent: parse the dooM! block from the user's init.el."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=UserInitConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )


def make_doom_module_analyzer_agent() -> Agent[None, DoomModuleData]:
    """Phase 3 agent: produce a DoomModuleData summary for one module."""
    return Agent(
        _make_model(config.CONFIG.models.extraction_model),
        output_type=DoomModuleData,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )


def make_translation_agent() -> Agent[None, TranslatedConfig]:
    """Phase 4 agent: vanilla → Doom translation (Pass 1)."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_4_HINTS,
        deps_type=type(None),
        retries=3,
    )
    # Register read tools so the agent can consult Doom defaults as needed
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_refinement_agent() -> Agent[None, TranslatedConfig]:
    """Phase 5 agent: integrate custom Elisp, refine transients (Pass 2)."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_5_HINTS,
        deps_type=type(None),
        retries=2,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_dedup_agent() -> Agent[None, TranslatedConfig]:
    """Phase 6 agent: deduplicate against Doom defaults."""
    agent = Agent(
        _make_model(config.CONFIG.models.translation_model),
        output_type=TranslatedConfig,
        system_prompt=DOOM_STITCHER_DIRECTIVE,
        deps_type=type(None),
        retries=2,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


def make_audit_agent() -> Agent[None, AuditReport]:
    """Phase 7 agent: comprehensive audit of the translated config."""
    agent = Agent(
        _make_model(config.CONFIG.models.audit_model),
        output_type=AuditReport,
        system_prompt=DOOM_STITCHER_DIRECTIVE + PHASE_7_HINTS,
        deps_type=type(None),
        retries=3,
    )
    for tool in get_agent_tools():
        agent.tool_plain(tool)
    return agent


# Single shared instances (agents are stateless; safe to reuse)
VANILLA_INGESTION_AGENT = make_vanilla_ingestion_agent()
USER_INIT_INGESTION_AGENT = make_user_init_ingestion_agent()
DOOM_MODULE_ANALYZER_AGENT = make_doom_module_analyzer_agent()
TRANSLATION_AGENT = make_translation_agent()
REFINEMENT_AGENT = make_refinement_agent()
DEDUP_AGENT = make_dedup_agent()
AUDIT_AGENT = make_audit_agent()
