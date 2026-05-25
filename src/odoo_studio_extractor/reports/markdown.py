"""Markdown rendering of the audit dataset."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _esc(value: Any) -> str:
    """Render a value safely inside a Markdown table cell."""
    if value is None or value is False:
        return ""
    if value is True:
        return "yes"
    if isinstance(value, (list, tuple)):
        # Common Odoo pattern: many2one returned as [id, "name"]
        if len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
            return f"{value[1]} (#{value[0]})"
        return ", ".join(_esc(v) for v in value)
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _section(title: str, level: int = 2) -> str:
    return f"{'#' * level} {title}\n\n"


def _table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    headers = list(headers)
    rows = [list(r) for r in rows]
    if not rows:
        return "_No records found._\n\n"
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = "\n".join("| " + " | ".join(_esc(c) for c in r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}\n\n"


def _model_of(record: dict[str, Any]) -> str:
    """Best-effort extraction of the model technical name from a record."""
    for key in ("model", "model_name", "res_model"):
        v = record.get(key)
        if isinstance(v, str) and v:
            return v
    mid = record.get("model_id")
    if isinstance(mid, list) and len(mid) == 2:
        return str(mid[1])
    return ""


# ---------------------------------------------------------------------- #
# Section renderers
# ---------------------------------------------------------------------- #
def _render_summary(data: dict[str, Any]) -> str:
    md = data["metadata"]
    counts = {
        "Studio / custom models": len(data.get("models", [])),
        "Studio / custom fields": len(data.get("fields", [])),
        "Modified or Studio views": len(data.get("views", [])),
        "Server actions": len(data.get("server_actions", [])),
        "Automated actions": len(data.get("automations", [])),
        "Menus": len(data.get("menus", [])),
        "Window actions": len(data.get("window_actions", [])),
        "Access rights": len(data.get("access_rights", [])),
        "Record rules": len(data.get("record_rules", [])),
    }

    out = _section("1. Executive Summary", level=2)
    out += (
        f"- **Odoo URL**: `{md.get('odoo_url', '')}`\n"
        f"- **Database**: `{md.get('odoo_db', '')}`\n"
        f"- **Audit user**: `{md.get('odoo_user', '')}`\n"
        f"- **Generated at (UTC)**: `{md.get('generated_at_utc', '')}`\n"
        f"- **Tool version**: `{md.get('tool_version', '')}`\n\n"
    )
    out += _table(
        ["Category", "Count"],
        [(k, v) for k, v in counts.items()],
    )
    warnings = md.get("warnings") or []
    if warnings:
        out += "**Warnings during extraction:**\n\n"
        for w in warnings:
            out += f"- {w}\n"
        out += "\n"
    return out


def _render_models(records: list[dict[str, Any]]) -> str:
    out = _section("2. Detected Studio / Custom Models")
    rows = [
        (
            r.get("id"),
            r.get("model"),
            r.get("name"),
            r.get("state"),
            r.get("transient"),
            r.get("modules"),
        )
        for r in records
    ]
    out += _table(
        ["ID", "Technical name", "Display name", "State", "Transient", "Modules"],
        rows,
    )
    return out


def _render_fields(records: list[dict[str, Any]]) -> str:
    out = _section("3. Detected Studio / Custom Fields (grouped by model)")
    if not records:
        return out + "_No records found._\n\n"

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        grouped[r.get("model") or "(unknown)"].append(r)

    for model in sorted(grouped):
        out += _section(f"`{model}`", level=3)
        rows = [
            (
                f.get("name"),
                f.get("field_description"),
                f.get("ttype"),
                f.get("relation"),
                f.get("required"),
                f.get("readonly"),
                f.get("store"),
                f.get("state"),
            )
            for f in grouped[model]
        ]
        out += _table(
            [
                "Name",
                "Label",
                "Type",
                "Relation",
                "Required",
                "Readonly",
                "Stored",
                "State",
            ],
            rows,
        )
    return out


def _render_views(records: list[dict[str, Any]]) -> str:
    out = _section("4. Modified or Studio-Generated Views (grouped by model)")
    if not records:
        return out + "_No records found._\n\n"

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        grouped[r.get("model") or "(no model)"].append(r)

    for model in sorted(grouped):
        out += _section(f"`{model}`", level=3)
        rows = [
            (
                v.get("id"),
                v.get("name"),
                v.get("type"),
                v.get("inherit_id"),
                v.get("priority"),
                v.get("active"),
                v.get("key"),
            )
            for v in grouped[model]
        ]
        out += _table(
            ["ID", "Name", "Type", "Inherits", "Priority", "Active", "Key"],
            rows,
        )
    return out


def _render_actions(data: dict[str, Any]) -> str:
    out = _section("5. Automated Actions and Server Actions")

    out += _section("Server actions (`ir.actions.server`)", level=3)
    rows = [
        (
            a.get("id"),
            a.get("name"),
            _model_of(a),
            a.get("state") or a.get("type"),
            a.get("usage"),
        )
        for a in data.get("server_actions", [])
    ]
    out += _table(["ID", "Name", "Model", "State / Type", "Usage"], rows)

    out += _section("Automated actions (`base.automation`)", level=3)
    rows = [
        (
            a.get("id"),
            a.get("name"),
            _model_of(a),
            a.get("trigger"),
            a.get("active"),
        )
        for a in data.get("automations", [])
    ]
    out += _table(["ID", "Name", "Model", "Trigger", "Active"], rows)
    return out


def _render_menus(data: dict[str, Any]) -> str:
    out = _section("6. Menus and Window Actions")

    out += _section("Window actions (`ir.actions.act_window`)", level=3)
    rows = [
        (
            a.get("id"),
            a.get("name"),
            a.get("res_model"),
            a.get("view_mode"),
            a.get("target"),
        )
        for a in data.get("window_actions", [])
    ]
    out += _table(["ID", "Name", "Model", "Views", "Target"], rows)

    out += _section("Menus (`ir.ui.menu`)", level=3)
    rows = [
        (
            m.get("id"),
            m.get("complete_name") or m.get("name"),
            m.get("parent_id"),
            m.get("action"),
            m.get("active"),
        )
        for m in data.get("menus", [])
    ]
    out += _table(["ID", "Path", "Parent", "Action", "Active"], rows)
    return out


def _render_security(data: dict[str, Any]) -> str:
    out = _section("7. Security and Access Rights")

    out += _section("Access rights (`ir.model.access`)", level=3)
    rows = [
        (
            r.get("id"),
            r.get("name"),
            r.get("model_id"),
            r.get("group_id"),
            r.get("perm_read"),
            r.get("perm_write"),
            r.get("perm_create"),
            r.get("perm_unlink"),
        )
        for r in data.get("access_rights", [])
    ]
    out += _table(
        ["ID", "Name", "Model", "Group", "Read", "Write", "Create", "Unlink"],
        rows,
    )

    out += _section("Record rules (`ir.rule`)", level=3)
    rows = [
        (
            r.get("id"),
            r.get("name"),
            r.get("model_id"),
            r.get("global"),
            r.get("domain_force"),
        )
        for r in data.get("record_rules", [])
    ]
    out += _table(["ID", "Name", "Model", "Global", "Domain"], rows)
    return out


def _render_inferred_logic(data: dict[str, Any]) -> str:
    out = _section("8. Inferred Business Logic")
    bullets: list[str] = []

    computed = [f for f in data.get("fields", []) if f.get("compute")]
    if computed:
        bullets.append(
            f"{len(computed)} computed field(s) detected — server-side Python "
            "code drives their values; review for migration."
        )
    related = [f for f in data.get("fields", []) if f.get("ttype") in ("many2one", "one2many", "many2many")]
    if related:
        bullets.append(
            f"{len(related)} relational field(s) detected — they describe how "
            "Studio entities are wired to the rest of Odoo."
        )
    autos = data.get("automations") or []
    if autos:
        bullets.append(
            f"{len(autos)} automated action(s) — these encode workflow rules "
            "(on create / on write / time-based)."
        )
    server_acts = data.get("server_actions") or []
    if server_acts:
        bullets.append(
            f"{len(server_acts)} server action(s) — typically Python or "
            "object-method actions triggered from buttons or automations."
        )
    if not bullets:
        return out + "_Nothing notable inferred from the extracted data._\n\n"

    for b in bullets:
        out += f"- {b}\n"
    return out + "\n"


def _render_migration_mapping(data: dict[str, Any]) -> str:
    out = _section("9. Migration Mapping")
    out += (
        "This section maps Studio artifacts to the equivalent components "
        "in a hand-written Odoo module, to support a Studio-to-code rebuild.\n\n"
    )
    out += _table(
        ["Studio artifact", "Module-equivalent location"],
        [
            ("Custom model (`x_*`)", "`models/<model>.py` (`class ... (models.Model)`)"),
            ("Studio field (`x_studio_*`)", "Field declared in the corresponding model class"),
            ("Studio view", "XML view in `views/<model>_views.xml`"),
            ("Window action", "`<record model='ir.actions.act_window'>` in `views/`"),
            ("Menu", "`<menuitem>` in `views/menus.xml`"),
            ("Automated action", "`base.automation` data record or Python in `models/`"),
            ("Server action", "`ir.actions.server` data record or method on the model"),
            ("Access rights", "`security/ir.model.access.csv`"),
            ("Record rules", "`<record model='ir.rule'>` in `security/security.xml`"),
        ],
    )
    return out


def _render_recommendations(data: dict[str, Any]) -> str:
    out = _section("10. Rebuild Recommendations")
    items = [
        "Create a dedicated custom Odoo module (e.g. `studio_rebuild`) to host "
        "all Studio artifacts as proper code.",
        "Reproduce custom models and fields in Python; keep `x_studio_` names "
        "during a transitional phase to preserve existing data, then rename in "
        "a controlled migration.",
        "Move view changes into XML views inheriting from the original views; "
        "avoid editing core views directly.",
        "Reimplement automations either as `base.automation` data records or "
        "as plain Python methods, depending on complexity.",
        "Move ACLs and record rules into `security/` files so they are "
        "version-controlled.",
        "Always test the rebuilt module on a staging copy before disabling "
        "Studio customizations on production.",
    ]
    for it in items:
        out += f"- {it}\n"
    return out + "\n"


def _render_risks(data: dict[str, Any]) -> str:
    out = _section("11. Risks and Unknowns")
    items = [
        "Detection is heuristic. Customizations not following `x_*` / "
        "`x_studio_*` conventions may be missed.",
        "Computed-field source code is exported as-is; its dependencies on "
        "other modules are not analyzed.",
        "View `arch_db` is exported as raw XML and not validated against the "
        "target Odoo version.",
        "Menus, ACLs and rules tied to standard models but added by Studio "
        "may require manual review if they don't match the heuristics.",
        "If the audit user does not have access to a given model, that "
        "section will be empty and a warning will appear in the metadata.",
    ]
    for it in items:
        out += f"- {it}\n"
    return out + "\n"


# ---------------------------------------------------------------------- #
# Public API
# ---------------------------------------------------------------------- #
def render_markdown_report(data: dict[str, Any]) -> str:
    """Render the full Markdown report from the extracted dataset."""
    out = "# Odoo Studio Audit Report\n\n"
    out += (
        "_Generated by **odoo-studio-extractor** in read-only mode._\n\n"
        "---\n\n"
    )
    out += _render_summary(data)
    out += _render_models(data.get("models", []))
    out += _render_fields(data.get("fields", []))
    out += _render_views(data.get("views", []))
    out += _render_actions(data)
    out += _render_menus(data)
    out += _render_security(data)
    out += _render_inferred_logic(data)
    out += _render_migration_mapping(data)
    out += _render_recommendations(data)
    out += _render_risks(data)
    return out


def write_markdown_report(data: dict[str, Any], path: Path | str) -> Path:
    """Render the Markdown report and write it to ``path``."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown_report(data), encoding="utf-8")
    return out.resolve()
