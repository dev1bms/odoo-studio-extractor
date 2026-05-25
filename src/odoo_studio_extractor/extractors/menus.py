"""Extract menus and window actions tied to custom / Studio models."""

from __future__ import annotations

from typing import Any, Iterable

from ..client import OdooClient, OdooClientError


MENU_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "complete_name",
    "parent_id",
    "sequence",
    "action",
    "active",
    "groups_id",
    "web_icon",
)


WINDOW_ACTION_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "res_model",
    "binding_model_id",
    "view_mode",
    "view_id",
    "domain",
    "context",
    "target",
    "usage",
    "help",
)


def extract_window_actions(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    custom_models: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return ``ir.actions.act_window`` whose ``res_model`` is a custom model."""
    warnings = warnings if warnings is not None else []
    models = list(custom_models or [])
    if not models:
        return []
    try:
        return client.search_read(
            "ir.actions.act_window",
            [("res_model", "in", models)],
            list(WINDOW_ACTION_FIELDS),
            order="res_model asc, name asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.actions.act_window extraction failed: {exc}")
        return []


def extract_menus(
    client: OdooClient,
    warnings: list[str] | None = None,
    *,
    window_action_ids: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Return ``ir.ui.menu`` records linked to the given window action ids.

    Odoo stores menu actions as a string of the form ``"ir.actions.act_window,42"``
    in the ``action`` field. We search by that string for each known
    window action id.
    """
    warnings = warnings if warnings is not None else []
    action_ids = list(window_action_ids or [])
    if not action_ids:
        return []

    action_refs = [f"ir.actions.act_window,{aid}" for aid in action_ids]
    domain: list[Any] = [("action", "in", action_refs)]

    try:
        return client.search_read(
            "ir.ui.menu",
            domain,
            list(MENU_FIELDS),
            order="complete_name asc",
        )
    except OdooClientError as exc:
        warnings.append(f"ir.ui.menu extraction failed: {exc}")
        return []
