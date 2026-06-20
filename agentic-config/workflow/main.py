#!/usr/bin/env python3
"""doom-stitcher — entry point.

Usage:
    python main.py                # run the full pipeline
    python main.py --dry-run      # same, but don't write files
    python main.py --no-stream    # batch mode (no live progress)
    python main.py --export-mermaid   # print the graph as Mermaid

~/.config/doom/workflow/main.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.panel import Panel

import config
from graph import GRAPH
from state import DoomStitcherState


console = Console()


def _initial_state() -> DoomStitcherState:
    paths = config.CONFIG.paths
    return DoomStitcherState(
        root_dir=str(paths.doomdir),
        workflow_dir=str(paths.workflow_dir),
        vanilla_config=None,
        user_init=None,
        enabled_modules=[],
        doom_module_data={},
        translated_config=None,
        refined_config=None,
        deduplicated_config=None,
        audit_report=None,
        final_config_org=None,
        final_readme=None,
        final_gitignore=None,
        final_setup_doom=None,
        final_files_written=[],
        maintenance_summary=None,
        errors=[],
        phase_status={},
        log_lines=[],
    )


def _apply_overrides(*, dry_run: bool, verbose: bool) -> None:
    """Rebuild the frozen ``WorkflowConfig`` if CLI flags changed it.

    Because ``WorkflowConfig`` is frozen, we must construct a new instance
    rather than mutate. ``paths`` and ``models`` are carried over unchanged.
    """
    current = config.CONFIG
    if dry_run == current.dry_run and verbose == current.verbose:
        return  # no-op; avoid rebuilding for nothing
    new_cfg = config.WorkflowConfig(
        paths=current.paths,
        models=current.models,
        verbose=verbose,
        dry_run=dry_run,
        skip_maintenance=current.skip_maintenance,
    )
    # Reassigning the module attribute is safe; every subsequent
    # ``config.CONFIG`` read in this process will see the new value.
    config.CONFIG = new_cfg


def _print_graph_mermaid() -> None:
    """Export the graph as Mermaid for documentation."""
    try:
        # LangGraph 1.2.x: get_graph() returns a Graph; draw_mermaid() returns str
        mermaid = GRAPH.get_graph().draw_mermaid()
        print(mermaid)
    except Exception as e:
        print(f"# Could not render Mermaid: {e}", file=sys.stderr)


def _serialize_audit_passed(result: DoomStitcherState) -> bool | None:
    """Safely extract audit_report.passed regardless of dict vs model object."""
    audit = result.get("audit_report")
    if audit is None:
        return None
    return getattr(audit, "passed", None)


def run() -> int:
    parser = argparse.ArgumentParser(
        description="doom-stitcher: vanilla → Doom translator"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not write output files"
    )
    parser.add_argument(
        "--no-stream", action="store_true", help="Disable streaming progress"
    )
    parser.add_argument(
        "--export-mermaid",
        action="store_true",
        help="Print the graph as Mermaid and exit",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    _apply_overrides(dry_run=args.dry_run, verbose=args.verbose)

    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.verbose else "INFO")

    if args.export_mermaid:
        _print_graph_mermaid()
        return 0

    console.print(
        Panel.fit(
            "[bold cyan]doom-stitcher[/bold cyan]  "
            f"v1.0.0\n"
            f"DOOMDIR: [green]{config.CONFIG.paths.doomdir}[/green]\n"
            f"Models: [yellow]{config.CONFIG.models.default_model}[/yellow] / "
            f"{config.CONFIG.models.translation_model} / "
            f"{config.CONFIG.models.audit_model}\n"
            f"LiteLLM: [blue]{config.CONFIG.models.base_url}[/blue]",
            title="🚀 Doom-Stitcher",
        )
    )

    initial = _initial_state()

    # Run the workflow ONCE. ``stream_mode="values"`` yields the full state
    # after each node, so the last value is the final state. Do NOT also
    # call ``invoke`` afterwards — that would re-run the whole pipeline.
    if args.no_stream:
        result = GRAPH.invoke(initial)
        for line in result.get("log_lines", []):
            console.print(f"  [dim]{line}[/dim]")
    else:
        result = initial
        with console.status(
            "[bold green]Running workflow…[/bold green]", spinner="dots"
        ):
            for state in GRAPH.stream(initial, stream_mode="values"):
                result = state
                # Stream each phase's log lines as they arrive
                for line in state.get("log_lines", []):
                    console.print(f"  [dim]{line}[/dim]")

    # ---- Summary ---------------------------------------------------------
    console.print()
    console.rule("[bold]Summary")

    errors = result.get("errors", [])
    audit = result.get("audit_report")
    files = result.get("final_files_written", [])

    if errors:
        console.print(f"[red]✗ {len(errors)} error(s):[/red]")
        for e in errors:
            console.print(f"  [red]•[/red] {e}")

    if audit is not None:
        console.print(
            f"\n[bold]Audit:[/bold] {len(audit.findings)} findings, "
            f"passed={audit.passed}"
        )
        for f in audit.findings[:10]:
            sev = getattr(f.severity, "value", str(f.severity))
            color = {"error": "red", "warning": "yellow", "info": "blue"}.get(
                sev, "white"
            )
            console.print(f"  [{color}]•[/{color}] {sev.upper()}: {f.message}")

    if files:
        console.print(f"\n[green]✓ Wrote {len(files)} file(s):[/green]")
        for f in files:
            console.print(f"  [green]•[/green] {f}")

    summary = result.get("maintenance_summary")
    if summary is not None:
        out = config.CONFIG.paths.state_dir / "maintenance-summary.json"
        console.print(f"\n[blue]Maintenance summary:[/blue] {out}")

    # Persist lightweight debug state (avoid serializing Pydantic models)
    debug_path = (
        config.CONFIG.paths.state_dir / f"state-{datetime.now():%Y%m%d-%H%M%S}.json"
    )
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        debug_path.write_text(
            json.dumps(
                {
                    "errors": list(result.get("errors", [])),
                    "phase_status": dict(result.get("phase_status", {})),
                    "files_written": list(result.get("final_files_written", [])),
                    "audit_passed": _serialize_audit_passed(result),
                },
                indent=2,
            )
        )
    except Exception as e:
        logger.warning(f"Could not write debug state: {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(run())
