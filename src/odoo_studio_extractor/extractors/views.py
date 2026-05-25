"""Extract Studio-modified or Studio-generated views from ``ir.ui.view``."""

from __future__ import annotations

from typing import Any, Iterable

from ..client import OdooClient, OdooClientError


VIEW_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "model",
    "type",
    "inherit_id",
    "priority",
    "active",
    "key",
    "arch_db",
)


def extract_views(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    custom_models: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return views likely created or modified by Odoo Studio.

    Detection criteria (OR):

    * ``arch_db`` contains ``x_studio_``
    * ``name`` contains ``Studio``
    * ``key`` contains ``studio``
    * ``model`` is one of the detected custom models
    """
    warnings = warnings if warnings is not None else []

    base_domain: list[Any] = [
        "|",
        "|",
        "|",
        ("arch_db", "ilike", "x_studio_"),
        ("name", "ilike", "studio"),
        ("key", "ilike", "studio"),
        ("model", "in", list(custom_models or ["__never__"])),
    ]

    try:
        records = client.search_read(
            "ir.ui.view",
            base_domain,
            list(VIEW_FIELDS),
            order="model asc, priority asc, id asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.ui.view extraction failed: {exc}")
        return []

    return records
