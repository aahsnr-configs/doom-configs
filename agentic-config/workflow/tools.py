"""Tools exposed to Pydantic AI agents.

These are *deterministic* I/O functions. They are the only way the agents
can read source files; this keeps the LLM from hallucinating file
contents and makes the workflow auditable.

~/.config/doom/workflow/tools.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


import config
from utils.elisp import (
    balanced_parens_check,
    extract_doom_macro_uses,
    extract_packages_from_packages_el,
    extract_setq_defaults,
)
from utils.org import extract_src_blocks

# ---------- Read tools -----------------------------------------------------


def read_text_file(path: str) -> str:
    """Read a UTF-8 text file. Returns empty string on error.

    For Doom module files, prefer `read_doom_module_file` which validates
    the path.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        return f"ERROR: file not found: {p}"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: could not read {p}: {e}"


def list_doom_modules() -> list[dict[str, Any]]:
    """List all Doom modules under doomemacs/modules/.

    Returns a list of {category, name, path, has_packages, has_config, has_init}.
    """
    modules_root = config.CONFIG.paths.modules_dir
    if not modules_root.is_dir():
        return []

    out: list[dict[str, Any]] = []
    for cat_dir in sorted(modules_root.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        for mod_dir in sorted(cat_dir.iterdir()):
            if not mod_dir.is_dir() or mod_dir.name.startswith("."):
                continue
            out.append(
                {
                    "category": cat_dir.name,
                    "name": mod_dir.name,
                    "path": str(
                        mod_dir.relative_to(config.CONFIG.paths.doomemacs_subdir)
                    ),
                    "has_packages": (mod_dir / "packages.el").is_file(),
                    "has_config": (mod_dir / "config.el").is_file(),
                    "has_init": (mod_dir / "init.el").is_file(),
                }
            )
    return out


def read_doom_module_file(category: str, name: str, filename: str) -> str:
    """Read a single file from a Doom module (e.g. config.el, packages.el).

    Validates that the path is within doomemacs/modules/ to prevent
    directory traversal.
    """
    mod_path = (config.CONFIG.paths.modules_dir / category / name).resolve()
    if not str(mod_path).startswith(str(config.CONFIG.paths.modules_dir.resolve())):
        return f"ERROR: invalid module path: {category}/{name}"
    file_path = mod_path / filename
    if not file_path.is_file():
        return f"ERROR: file not found: {file_path}"
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: could not read {file_path}: {e}"


def search_doom_modules(
    pattern: str, file_glob: str = "*.el", max_results: int = 20
) -> list[dict[str, str]]:
    """Search across all Doom module files for a regex pattern.

    Returns a list of {path, line_number, line} matches.
    """
    modules_root = config.CONFIG.paths.modules_dir
    if not modules_root.is_dir():
        return []

    matches: list[dict[str, str]] = []
    try:
        rg = re.compile(pattern)
    except re.error as e:
        return [{"error": f"invalid regex: {e}"}]

    for path in modules_root.rglob(file_glob):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rg.search(line):
                matches.append(
                    {
                        "path": str(
                            path.relative_to(config.CONFIG.paths.doomemacs_subdir)
                        ),
                        "line": str(i),
                        "text": line[:200],
                    }
                )
                if len(matches) >= max_results:
                    return matches
    return matches


# ---------- Parse tools ---------------------------------------------------


def parse_org_src_blocks_tool(path: str) -> list[dict[str, Any]]:
    """Extract org-mode src blocks from a file, returning a serialized form."""
    p = Path(path).expanduser()
    if not p.is_file():
        return [{"error": f"file not found: {p}"}]
    text = p.read_text(encoding="utf-8")
    blocks = extract_src_blocks(text)
    return [
        {
            "lang": b.lang,
            "tangle": b.tangle,
            "headers": b.headers,
            "body_preview": b.body[:300],
            "body_length": len(b.body),
            "start_line": b.start_line,
            "end_line": b.end_line,
        }
        for b in blocks
    ]


def parse_packages_el_tool(path: str) -> dict[str, str]:
    """Parse a packages.el file and return {package_name: full_form}."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    return extract_packages_from_packages_el(p.read_text(encoding="utf-8"))


def extract_setq_defaults_tool(path: str) -> dict[str, str]:
    """Parse a config.el-ish file and return {var_name: value_expression}."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    return extract_setq_defaults(p.read_text(encoding="utf-8"))


def extract_doom_macros_tool(path: str) -> list[str]:
    """Return the set of Doom-specific macros used in a file."""
    p = Path(path).expanduser()
    if not p.is_file():
        return [f"ERROR: file not found: {p}"]
    return sorted(extract_doom_macro_uses(p.read_text(encoding="utf-8")))


def validate_elisp_balance_tool(path: str) -> dict[str, Any]:
    """Check paren balance of an Elisp file."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"file not found: {p}"}
    text = p.read_text(encoding="utf-8")
    ok, max_d = balanced_parens_check(text)
    return {"balanced": ok, "max_depth": max_d, "line_count": text.count("\n") + 1}


# ---------- Write tools (Phase 8) ----------------------------------------


def write_text_file_tool(path: str, content: str) -> dict[str, Any]:
    """Write a text file (Phase 8 only). Creates parent dirs as needed."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"written": str(p), "bytes": len(content)}


def move_file_tool(src: str, dst: str) -> dict[str, Any]:
    """Move a file, creating parent dirs on the destination."""
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return {"error": f"source not found: {s}"}
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    return {"moved": {"from": str(s), "to": str(d)}}


def remove_directory_tool(path: str) -> dict[str, Any]:
    """Remove a directory recursively. Used to delete the emacs/ folder."""
    import shutil

    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"path not found: {p}"}
    if p.is_file():
        return {"error": f"refusing to remove file: {p}"}
    # Safety: only remove if it's named 'emacs' and under our doomdir
    if p.name != "emacs":
        return {"error": f"refusing to remove non-emacs directory: {p}"}
    if not str(p.resolve()).startswith(str(config.CONFIG.paths.doomdir.resolve())):
        return {"error": f"refusing to remove path outside DOOMDIR: {p}"}
    shutil.rmtree(p)
    return {"removed": str(p)}


# ---------- Toolset registration -----------------------------------------


def get_agent_tools() -> list:
    """Return the list of tools to register on each agent.

    We register the read/parse/search tools; the write/move/remove tools
    are registered only on the Phase 8 output-generation agent.
    """
    return [
        read_text_file,
        list_doom_modules,
        read_doom_module_file,
        search_doom_modules,
        parse_org_src_blocks_tool,
        parse_packages_el_tool,
        extract_setq_defaults_tool,
        extract_doom_macros_tool,
        validate_elisp_balance_tool,
    ]


def get_writer_tools() -> list:
    return [
        write_text_file_tool,
        move_file_tool,
        remove_directory_tool,
    ]
