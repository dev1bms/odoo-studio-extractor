"""XML-RPC Odoo client, restricted to read-only operations.

This module is the **only** place in the project that talks to Odoo. It
deliberately exposes a minimal surface:

* :py:meth:`OdooClient.authenticate`
* :py:meth:`OdooClient.search`
* :py:meth:`OdooClient.read`
* :py:meth:`OdooClient.search_read`
* :py:meth:`OdooClient.count`

Any attempt to invoke a non-allowed Odoo method through the internal
``_execute`` helper raises :class:`UnsafeOperationError`.
"""

from __future__ import annotations

import socket
import xmlrpc.client
from typing import Any, Iterable, Sequence

from .config import OdooConfig


# Odoo methods that are considered safe (read-only).
ALLOWED_METHODS: frozenset[str] = frozenset(
    {
        "search",
        "read",
        "search_read",
        "search_count",
        "fields_get",
        "default_get",
    }
)


class OdooClientError(RuntimeError):
    """Base error for OdooClient failures."""


class OdooConnectionError(OdooClientError):
    """Raised when the XML-RPC endpoint cannot be reached."""


class OdooAuthenticationError(OdooClientError):
    """Raised when authentication fails."""


class UnsafeOperationError(OdooClientError):
    """Raised when a non-read-only Odoo method is requested."""


class OdooClient:
    """Minimal, read-only XML-RPC client for Odoo.

    The client never exposes ``create``, ``write``, ``unlink``, ``execute``,
    ``execute_kw`` directly to callers. Internally, ``execute_kw`` is used
    only with a method name from :data:`ALLOWED_METHODS`.
    """

    def __init__(self, config: OdooConfig, *, timeout: float = 30.0) -> None:
        self._config = config
        self._timeout = timeout
        self._uid: int | None = None
        self._common: xmlrpc.client.ServerProxy | None = None
        self._models: xmlrpc.client.ServerProxy | None = None

    # ------------------------------------------------------------------ #
    # Connection / authentication
    # ------------------------------------------------------------------ #
    def _build_proxy(self, path: str) -> xmlrpc.client.ServerProxy:
        url = f"{self._config.url}/xmlrpc/2/{path}"
        try:
            return xmlrpc.client.ServerProxy(url, allow_none=True)
        except Exception as exc:  # pragma: no cover - defensive
            raise OdooConnectionError(
                f"Failed to build XML-RPC proxy for {url}: {exc}"
            ) from exc

    def authenticate(self) -> int:
        """Authenticate against Odoo and cache the user id."""
        if self._uid is not None:
            return self._uid

        # Apply a default socket timeout for XML-RPC calls.
        socket.setdefaulttimeout(self._timeout)

        self._common = self._build_proxy("common")
        try:
            uid = self._common.authenticate(
                self._config.db,
                self._config.username,
                self._config.password,
                {},
            )
        except (xmlrpc.client.Fault, OSError, socket.error) as exc:
            raise OdooConnectionError(
                f"Could not reach Odoo at {self._config.url}: {exc}"
            ) from exc

        if not uid:
            raise OdooAuthenticationError(
                "Authentication failed: invalid database, username or password."
            )

        self._uid = int(uid)
        self._models = self._build_proxy("object")
        return self._uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            return self.authenticate()
        return self._uid

    # ------------------------------------------------------------------ #
    # Internal safe execute
    # ------------------------------------------------------------------ #
    def _execute(
        self,
        model: str,
        method: str,
        args: Sequence[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a whitelisted Odoo method via ``execute_kw``.

        Raises
        ------
        UnsafeOperationError
            If ``method`` is not in :data:`ALLOWED_METHODS`.
        """
        if method not in ALLOWED_METHODS:
            raise UnsafeOperationError(
                f"Method '{method}' is not allowed. "
                f"odoo-studio-extractor is read-only and only permits: "
                f"{sorted(ALLOWED_METHODS)}."
            )

        uid = self.uid
        assert self._models is not None  # for type-checkers

        try:
            return self._models.execute_kw(
                self._config.db,
                uid,
                self._config.password,
                model,
                method,
                list(args or []),
                dict(kwargs or {}),
            )
        except xmlrpc.client.Fault as exc:
            raise OdooClientError(
                f"Odoo returned a fault calling {model}.{method}: "
                f"{exc.faultString}"
            ) from exc
        except (OSError, socket.error) as exc:
            raise OdooConnectionError(
                f"Network error calling {model}.{method}: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Public read-only API
    # ------------------------------------------------------------------ #
    def search(
        self,
        model: str,
        domain: Iterable[Any] | None = None,
        *,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[int]:
        """Return a list of record ids matching ``domain``."""
        kwargs: dict[str, Any] = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
        return list(
            self._execute(model, "search", [list(domain or [])], kwargs)
        )

    def read(
        self,
        model: str,
        ids: Sequence[int],
        fields: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read the given record ids and return a list of dicts."""
        if not ids:
            return []
        kwargs: dict[str, Any] = {}
        if fields is not None:
            kwargs["fields"] = list(fields)
        return list(self._execute(model, "read", [list(ids)], kwargs))

    def search_read(
        self,
        model: str,
        domain: Iterable[Any] | None = None,
        fields: Sequence[str] | None = None,
        *,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Combined ``search`` + ``read`` in a single round trip."""
        kwargs: dict[str, Any] = {"offset": offset}
        if fields is not None:
            kwargs["fields"] = list(fields)
        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order
        return list(
            self._execute(model, "search_read", [list(domain or [])], kwargs)
        )

    def count(
        self,
        model: str,
        domain: Iterable[Any] | None = None,
    ) -> int:
        """Return the number of records matching ``domain``."""
        return int(
            self._execute(model, "search_count", [list(domain or [])])
        )

    # ------------------------------------------------------------------ #
    # Discovery helpers (still read-only)
    # ------------------------------------------------------------------ #
    def model_exists(self, model: str) -> bool:
        """Return ``True`` if ``model`` is registered in the target Odoo."""
        try:
            ids = self.search("ir.model", [("model", "=", model)], limit=1)
        except OdooClientError:
            return False
        return bool(ids)

    def fields_get(
        self,
        model: str,
        attributes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Return field metadata for ``model``."""
        kwargs: dict[str, Any] = {}
        if attributes is not None:
            kwargs["attributes"] = list(attributes)
        return dict(self._execute(model, "fields_get", [], kwargs))
