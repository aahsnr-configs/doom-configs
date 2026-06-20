"""Lightweight, regex-based Elisp parsing.

We deliberately avoid full S-expression parsing — it adds a heavy dep
(sexpdata, sexp_parser) for limited gain. Doom configs follow conventions
that regex handles well: `(defun NAME`, `(defcustom NAME`, `(setq VAR`,
`(package! NAME ...)`, `(after! FEATURE`, `(map! ...)`, etc.

~/.config/doom/workflow/utils/elisp.py
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# Capture (head . args) where head is a symbol and args extends to the
# matching closing paren at depth 0. This handles nested forms correctly
# in the common case because we don't go deeper than 4-5 levels.
_FORM_RE = re.compile(
    r"\(([a-zA-Z!_\-\*\+\?<>=&%^/]+)([^()]*(?:\([^()]*\)[^()]*)*)\)", re.DOTALL
)


def iter_forms(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield (head, args_text, full_form) for each top-level s-expression.

    Note: this is a *simple* parser; for deeply nested forms it may
    mis-segment. It is sufficient for Doom configs, which use shallow
    nesting in the patterns we care about.
    """
    for m in _FORM_RE.finditer(text):
        head, args, full = m.group(1), m.group(2), m.group(0)
        yield head, args, full


def extract_packages_from_packages_el(text: str) -> dict[str, str]:
    """Parse a `packages.el` and return {package_name: full_form}."""
    out: dict[str, str] = {}
    for head, args, full in iter_forms(text):
        if head == "package!":
            name = args.split()[0] if args.split() else ""
            if name:
                out[name] = full.strip()
    return out


def extract_setq_defaults(text: str) -> dict[str, str]:
    """Parse `config.el`-ish text and return {var_name: value_expr}."""
    out: dict[str, str] = {}
    for head, args, full in iter_forms(text):
        if head == "setq":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
        elif head == "setq!":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
        elif head == "setq-default":
            tokens = args.split(None, 1)
            if len(tokens) == 2:
                out[tokens[0]] = tokens[1].strip()
    return out


def extract_keybindings(text: str) -> list[dict[str, str]]:
    """Best-effort extraction of `map!` and `global-set-key` definitions."""
    out: list[dict[str, str]] = []
    for head, args, full in iter_forms(text):
        if head in ("map!", "global-set-key", "local-set-key"):
            out.append({"head": head, "raw": full.strip()})
    return out


def extract_doom_macro_uses(text: str) -> set[str]:
    """Collect all Doom-specific macro names used in the text."""
    macro_heads: set[str] = set()
    for head, _, _ in iter_forms(text):
        if head.endswith("!") or head in {"def-hydra", "map!"}:
            macro_heads.add(head)
    return macro_heads


def balanced_parens_check(text: str) -> tuple[bool, int]:
    """Return (ok, max_depth). Naive but useful for sanity checks."""
    depth = 0
    max_d = 0
    in_string = False
    in_comment = False
    esc = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_comment:
            if c == "\n":
                in_comment = False
        elif in_string:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_string = False
        else:
            if c == ";":
                in_comment = True
            elif c == '"':
                in_string = True
            elif c == "(":
                depth += 1
                max_d = max(max_d, depth)
            elif c == ")":
                depth -= 1
                if depth < 0:
                    return False, max_d
        i += 1
    return depth == 0, max_d
