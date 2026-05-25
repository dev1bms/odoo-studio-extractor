"""Read-only extractors for Odoo Studio customizations.

Each module in this package exposes one or more functions that take an
:class:`~odoo_studio_extractor.client.OdooClient` instance and return
plain Python data structures (lists / dicts) ready to be serialized.

Extractors are designed to be resilient: if a model is missing or the
authenticated user lacks access, they return empty data and append a
warning to a shared list rather than crashing.
"""

from __future__ import annotations

from .actions import extract_automations, extract_server_actions
from .fields import extract_fields, is_studio_field
from .menus import extract_menus, extract_window_actions
from .models import extract_models, is_studio_model
from .security import extract_access_rights, extract_record_rules
from .views import extract_views

__all__ = [
    "extract_models",
    "is_studio_model",
    "extract_fields",
    "is_studio_field",
    "extract_views",
    "extract_server_actions",
    "extract_automations",
    "extract_menus",
    "extract_window_actions",
    "extract_access_rights",
    "extract_record_rules",
]
