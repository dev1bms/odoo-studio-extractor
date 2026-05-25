"""Extract security records (access rights and record rules)."""

from __future__ import annotations

from typing import Any, Iterable

from ..client import OdooClient, OdooClientError


ACCESS_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "model_id",
    "group_id",
    "perm_read",
    "perm_write",
    "perm_create",
    "perm_unlink",
    "active",
)


RULE_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "model_id",
    "groups",
    "domain_force",
    "perm_read",
    "perm_write",
    "perm_create",
    "perm_unlink",
    "active",
    "global",
)


def _ensure_model_ids(
    client: OdooClient,
    custom_models: Iterable[str] | None,
    warnings: list[str],
) -> list[int]:
    """Resolve model technical names into ``ir.model`` ids."""
    models = list(custom_models or [])
    if not models:
        return []
    try:
        records = client.search_read(
            "ir.model",
            [("model", "in", models)],
            ["id", "model"],
        )
    except OdooClientError as exc:
        warnings.append(f"ir.model lookup failed during security extraction: {exc}")
        return []
    return [r["id"] for r in records]


def extract_access_rights(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    custom_models: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return ``ir.model.access`` rows targeting custom / Studio models."""
    warnings = warnings if warnings is not None else []
    model_ids = _ensure_model_ids(client, custom_models, warnings)
    if not model_ids:
        return []
    try:
        return client.search_read(
            "ir.model.access",
            [("model_id", "in", model_ids)],
            list(ACCESS_FIELDS),
            order="name asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.model.access extraction failed: {exc}")
        return []


def extract_record_rules(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    custom_models: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return ``ir.rule`` rows targeting custom / Studio models."""
    warnings = warnings if warnings is not None else []
    model_ids = _ensure_model_ids(client, custom_models, warnings)
    if not model_ids:
        return []
    try:
        return client.search_read(
            "ir.rule",
            [("model_id", "in", model_ids)],
            list(RULE_FIELDS),
            order="name asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.rule extraction failed: {exc}")
        return []
