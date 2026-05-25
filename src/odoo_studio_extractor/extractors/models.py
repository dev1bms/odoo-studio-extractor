"""Extract Studio / custom Odoo models from ``ir.model``."""

from __future__ import annotations

from typing import Any

from ..client import OdooClient, OdooClientError


MODEL_FIELDS: tuple[str, ...] = (
    "id",
    "model",
    "name",
    "state",
    "transient",
    "modules",
    "info",
)


def is_studio_model(record: dict[str, Any]) -> bool:
    """Heuristic: does this ``ir.model`` record look Studio/custom?"""
    model_name = (record.get("model") or "").strip()
    state = (record.get("state") or "").strip()
    if model_name.startswith("x_"):
        return True
    if state == "manual":
        return True
    return False


def extract_models(
    client: OdooClient,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return Studio / custom-looking ``ir.model`` records.

    Detection criteria (any of):

    * model technical name starts with ``x_``
    * ``state == 'manual'``
    """
    warnings = warnings if warnings is not None else []
    domain = ["|", ("model", "=like", "x\\_%"), ("state", "=", "manual")]
    try:
        records = client.search_read(
            "ir.model",
            domain,
            list(MODEL_FIELDS),
            order="model asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.model extraction failed: {exc}")
        return []

    cleaned: list[dict[str, Any]] = []
    for rec in records:
        rec["is_studio_like"] = is_studio_model(rec)
        cleaned.append(rec)
    return cleaned
