"""Pydantic v2 models representing every typed payload in the workflow.

These are the contracts that flow through LangGraph state. Every agent's output is validated against one of these models, ensuring the LLM cannot inject malformed data into the next phase.

~/.config/doom/workflow/models.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Enums ----------------------------------------------------------


class DoomModuleCategory(str, Enum):
    """Official Doom module categories (from doomemacs/modules/*/)."""

    APP = "app"
    CHECKERS = "checkers"
    COMPLETION = "completion"
    CONFIG = "config"
    EDITOR = "editor"
    EMACS = "emacs"
    EMAIL = "email"
    INPUT = "input"
    LANG = "lang"
    OS = "os"
    TERM = "term"
    TOOLS = "tools"
    UI = "ui"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# ---------- Vanilla ingestion (Phase 1) ----------------------------------


class VanillaPackage(BaseModel):
    """A package declared in the vanilla config."""

    name: str
    source: str | None = None  # e.g. "melpa", "gnu", "quelpa", or recipe
    version_pin: str | None = None
    use_package_block: str | None = None  # raw elisp for reference


class VanillaKeybinding(BaseModel):
    """A keybinding extracted from vanilla config."""

    keys: str
    command: str
    mode: str | None = None  # global, local, or specific-mode
    raw_definition: str | None = None


class VanillaCustomDef(BaseModel):
    """A custom function, defhydra, transient, advice, etc."""

    kind: Literal[
        "defun",
        "defmacro",
        "defhydra",
        "defvar",
        "defcustom",
        "transient",
        "advice",
        "other",
    ]
    name: str
    body: str
    source_location: str | None = None  # e.g. "emacs/config.org::Custom defuns"


class VanillaConfig(BaseModel):
    """Aggregate of everything extracted from the vanilla configs."""

    packages: list[VanillaPackage] = Field(default_factory=list)
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)
    custom_defs: list[VanillaCustomDef] = Field(default_factory=list)
    early_init_settings: list[str] = Field(
        default_factory=list
    )  # raw early-init.el lines
    notes: str = ""
    source_org_path: str | None = None
    source_early_init_path: str | None = None

    @field_validator("packages", "keybindings", "custom_defs", mode="before")
    @classmethod
    def _accept_none(cls, v: Any) -> Any:
        return v or []


# ---------- User init.el ingestion (Phase 2) -----------------------------


class DoomModuleFlag(BaseModel):
    """A flag applied to a module, e.g. :completion company +tng."""

    name: str
    value: str | bool = True  # boolean for bare flags, str for +flag=value


class DoomModule(BaseModel):
    """A single enabled Doom module from the user's init.el."""

    category: DoomModuleCategory
    name: str
    flags: list[DoomModuleFlag] = Field(default_factory=list)

    @property
    def path(self) -> str:
        return f"{self.category.value}/{self.name}"


class UserInitConfig(BaseModel):
    """The full dooM! block as parsed from the user's init.el."""

    modules: list[DoomModule]
    raw_doom_block: str
    source_path: str


# ---------- Doom module ingestion (Phase 3) -----------------------------


class DoomModuleFile(BaseModel):
    """A single file (config.el, init.el, packages.el) of a Doom module."""

    filename: str  # e.g. "config.el"
    content: str
    relevant_sections: list[str] = Field(
        default_factory=list
    )  # names of defuns/sections we care about


class DoomModuleData(BaseModel):
    """All files + extracted defaults for a Doom module."""

    category: str
    name: str
    path: str  # e.g. "ui/treemacs"
    files: list[DoomModuleFile] = Field(default_factory=list)

    # Quick-lookup: variable name → default value expression (string)
    defaults: dict[str, str] = Field(default_factory=dict)
    # Quick-lookup: package name → recipe/flag (e.g. "package! treemacs")
    packages: dict[str, str] = Field(default_factory=dict)
    # Quick-lookup: keybinding pattern → definition
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)
    # macrology this module uses (after!, use-package!, etc.)
    macros_used: list[str] = Field(default_factory=list)


# ---------- Translation outputs (Phases 4-6) ----------------------------


class InitElBlock(BaseModel):
    """The init.el source block content (the dooM! macro + early settings)."""

    doom_block: str
    extra_early_settings: str = ""


class PackagesElBlock(BaseModel):
    """The packages.el source block content."""

    package_declarations: list[str] = Field(
        default_factory=list
    )  # each a (package! ...) form
    recipes: list[str] = Field(default_factory=list)  # each a (recipe! ...) form
    pins: list[str] = Field(default_factory=list)  # each a (pin ...) form


class ConfigElBlock(BaseModel):
    """The config.el source block content."""

    load_path_setup: str = ""
    after_org_setup: str = ""  # contains (require 'org-src-context)
    config_forms: list[str] = Field(
        default_factory=list
    )  # each a (after! ...)/(use-package! ...)/(setq ...)
    custom_defs: list[VanillaCustomDef] = Field(default_factory=list)
    transient_defs: list[str] = Field(default_factory=list)
    keybindings: list[VanillaKeybinding] = Field(default_factory=list)


class TranslatedConfig(BaseModel):
    """A single translated configuration, ready to be rendered into config.org."""

    init_el: InitElBlock
    packages_el: PackagesElBlock
    config_el: ConfigElBlock
    preamble: str = ""  # top-of-file org keywords


# ---------- Audit (Phase 7) -----------------------------------------------


class AuditFinding(BaseModel):
    severity: Severity
    category: str  # e.g. "macro-validity", "duplicate", "tangle"
    message: str
    location: str | None = None  # e.g. "config.el src block"
    suggested_fix: str | None = None


class AuditReport(BaseModel):
    findings: list[AuditFinding] = Field(default_factory=list)
    passed: bool = True
    summary: str = ""

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)
        if finding.severity == Severity.ERROR:
            self.passed = False


# ---------- Maintenance (Phase 9) ----------------------------------------


class MaintenanceSummary(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    doomemacs_commit: str | None = None
    doom_modules_tracked: list[str] = Field(default_factory=list)
    override_setpoints: list[str] = Field(
        default_factory=list
    )  # settings that explicitly override Doom defaults
    upstream_changes_to_review: list[str] = Field(default_factory=list)
    config_fingerprint: str  # hash of final config.org, used to detect drift

    model_config = ConfigDict(arbitrary_types_allowed=True)
