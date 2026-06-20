"""Doom-Stitcher runtime directive loader.

The actual prompt content lives in XML files under workflow/prompts/.
This module:
  1. Locates the prompts directory relative to this file.
  2. Parses each ``<directive>`` XML file (CDATA-wrapped markdown).
  3. Exposes module-level constants that other modules import.
  4. Caches the loaded content (loaded once at import time).

Storing the prompts as XML files (rather than Python triple-quoted strings) eliminates the syntax hazards of embedding markdown — with its triple backticks, escaped backslashes, f-string braces, and embedded code samples — directly in source code. It also keeps the prompt engineering content out of version-control diffs for the application logic.

~/.config/doom/workflow/prompt.py
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

# Resolved once at import time. ``Path(__file__).resolve().parent`` is the
# workflow/ directory; the prompts live in workflow/prompts/.
_PROMPTS_DIR: Path = Path(__file__).resolve().parent / "prompts"


@lru_cache(maxsize=8)
def _load_xml_directive(filename: str) -> str:
    """Load a ``<directive>`` XML file and return its ``<content>`` CDATA text.

    The XML structure is::

        <directive id="..." version="...">
            <metadata>...</metadata>
            <content><![CDATA[...markdown body...]]></content>
        </directive>

    The CDATA wrapper preserves triple backticks, ampersands, and angle
    brackets verbatim — none of which would survive as a Python string
    literal without escape-hell.
    """
    path = _PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    content_elem = root.find("content")
    if content_elem is None or content_elem.text is None:
        raise ValueError(f"Prompt file {path} has no <content> element or empty body")
    return content_elem.text.strip()


# ---------- Public constants -----------------------------------------------
# These are imported by ``agents.py`` and concatenated with the base
# directive for per-phase agent factory functions. Loaded once, cached.

DOOM_STITCHER_DIRECTIVE: str = _load_xml_directive("directive.xml")
PHASE_4_HINTS: str = _load_xml_directive("phase4_hints.xml")
PHASE_5_HINTS: str = _load_xml_directive("phase5_hints.xml")
PHASE_7_HINTS: str = _load_xml_directive("phase7_hints.xml")


def get_prompts_dir() -> Path:
    """Return the prompts directory (useful for diagnostics / `--debug`)."""
    return _PROMPTS_DIR
