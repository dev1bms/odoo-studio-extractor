"""Extract Studio / custom Odoo fields from ``ir.model.fields``."""

from __future__ import annotations

from typing import Any, Iterable

from ..client import OdooClient, OdooClientError


FIELD_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "field_description",
    "model",
    "model_id",
    "ttype",
    "relation",
    "required",
    "readonly",
    "store",
    "index",
    "copied",
    "selection",
    "help",
    "compute",
    "depends",
    "state",
)


def is_studio_field(record: dict[str, Any]) -> bool:
    """Heuristic: does this ``ir.model.fields`` record look like a Studio field?"""
    name = (record.get("name") or "").strip()
    state = (record.get("state") or "").strip()
    if name.startswith("x_studio_"):
        return True
    if name.startswith("x_") and state == "manual":
        return True
    return False


def extract_fields(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    extra_models: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return Studio / custom-looking ``ir.model.fields`` records.

    Detection criteria (OR):

    * ``name`` starts with ``x_studio_``
    * ``state == 'manual'``
    * ``model`` is in ``extra_models`` (typically the custom models we already
      detected, so we also pull their non-``x_studio_`` fields).
    """
    warnings = warnings if warnings is not None else []
    domain: list[Any] = [
        "|",
        "|",
        ("name", "=like", "x\\_studio\\_%"),
        ("state", "=", "manual"),
        ("model", "in", list(extra_models or [])),
    ] if extra_models else [
        "|",
        ("name", "=like", "x\\_studio\\_%"),
        ("state", "=", "manual"),
    ]

    try:
        records = client.search_read(
            "ir.model.fields",
            domain,
            list(FIELD_FIELDS),
            order="model asc, name asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.model.fields extraction failed: {exc}")
        return []

    for rec in records:
        rec["is_studio_like"] = is_studio_field(rec)
    return records
