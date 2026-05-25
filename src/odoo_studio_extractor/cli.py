"""Command-line interface for odoo-studio-extractor."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .client import OdooAuthenticationError, OdooClient, OdooClientError, OdooConnectionError
from .config import ConfigError, load_config
from .extractors import (
    extract_access_rights,
    extract_automations,
    extract_fields,
    extract_menus,
    extract_models,
    extract_record_rules,
    extract_server_actions,
    extract_views,
    extract_window_actions,
)
from .reports import write_json_report, write_markdown_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odoo-studio-extractor",
        description=(
            "Read-only auditor for Odoo Studio customizations. "
            "Connects to an Odoo instance via XML-RPC and exports custom "
            "models, fields, views, actions, menus and security rules to "
            "Markdown and JSON."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit",
        help="Run a full Studio audit and write Markdown + JSON reports.",
    )
    audit.add_argument(
        "--output",
        "-o",
        default="outputs/studio_audit",
        help="Output directory (default: outputs/studio_audit).",
    )
    audit.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="XML-RPC socket timeout in seconds (default: 30).",
    )
    return parser


def _run_audit(client: OdooClient) -> dict[str, Any]:
    """Run all extractors and return a structured dataset."""
    warnings: list[str] = []

    models = extract_models(client, warnings)
    custom_model_names = [m["model"] for m in models if m.get("model")]

    fields = extract_fields(
        client,
        warnings,
        extra_models=custom_model_names,
    )

    # Augment list of "interesting" models with any model that has Studio fields
    models_with_studio_fields = sorted(
        {f.get("model") for f in fields if f.get("model")}
    )
    interesting_models = sorted(
        set(custom_model_names) | set(models_with_studio_fields)
    )

    views = extract_views(client, warnings, custom_models=interesting_models)
    server_actions = extract_server_actions(
        client, warnings, custom_models=interesting_models
    )
    automations = extract_automations(
        client, warnings, custom_models=interesting_models
    )
    window_actions = extract_window_actions(
        client, warnings, custom_models=interesting_models
    )
    menus = extract_menus(
        client,
        warnings,
        window_action_ids=[a["id"] for a in window_actions if a.get("id")],
    )
    access_rights = extract_access_rights(
        client, warnings, custom_models=interesting_models
    )
    record_rules = extract_record_rules(
        client, warnings, custom_models=interesting_models
    )

    return {
        "metadata": {
            "tool": "odoo-studio-extractor",
            "tool_version": __version__,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "odoo_url": client._config.url,  # noqa: SLF001 - safe, no secret
            "odoo_db": client._config.db,    # noqa: SLF001
            "odoo_user": client._config.username,  # noqa: SLF001
            "warnings": warnings,
            "interesting_models": interesting_models,
        },
        "models": models,
        "fields": fields,
        "views": views,
        "server_actions": server_actions,
        "automations": automations,
        "menus": menus,
        "window_actions": window_actions,
        "access_rights": access_rights,
        "record_rules": record_rules,
    }


def _print_summary(data: dict[str, Any], md_path: Path, json_path: Path) -> None:
    print("Studio audit complete.")
    print(f"  Models       : {len(data.get('models', []))}")
    print(f"  Fields       : {len(data.get('fields', []))}")
    print(f"  Views        : {len(data.get('views', []))}")
    print(f"  Server acts. : {len(data.get('server_actions', []))}")
    print(f"  Automations  : {len(data.get('automations', []))}")
    print(f"  Menus        : {len(data.get('menus', []))}")
    print(f"  Window acts. : {len(data.get('window_actions', []))}")
    print(f"  Access rules : {len(data.get('access_rights', []))}")
    print(f"  Record rules : {len(data.get('record_rules', []))}")
    print(f"  Markdown : {md_path}")
    print(f"  JSON     : {json_path}")
    warnings = data.get("metadata", {}).get("warnings") or []
    if warnings:
        print(f"  Warnings : {len(warnings)} (see report metadata)")


def _cmd_audit(args: argparse.Namespace) -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    client = OdooClient(config, timeout=args.timeout)

    try:
        client.authenticate()
    except OdooAuthenticationError as exc:
        print(f"Authentication failed: {exc}", file=sys.stderr)
        return 3
    except OdooConnectionError as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        return 4
    except OdooClientError as exc:
        print(f"Odoo client error: {exc}", file=sys.stderr)
        return 5

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _run_audit(client)

    md_path = write_markdown_report(data, output_dir / "studio_report.md")
    json_path = write_json_report(data, output_dir / "studio_data.json")
    _print_summary(data, md_path, json_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        return _cmd_audit(args)
    parser.error(f"Unknown command: {args.command}")
    return 1  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
