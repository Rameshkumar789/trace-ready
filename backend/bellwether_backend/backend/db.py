from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from bellwether_backend.api.config import ServiceSettings


class DatabaseConfigurationError(RuntimeError):
    pass


def open_supabase_connection(settings: ServiceSettings) -> Any:
    if not settings.database_url:
        raise DatabaseConfigurationError(
            "SUPABASE_DATABASE_URL is required for Python worker access to Supabase tables."
        )
    if settings.database_url.startswith(("http://", "https://")):
        raise DatabaseConfigurationError(
            "SUPABASE_DATABASE_URL must be the Supabase table connection string, not the Supabase project API URL."
        )

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise DatabaseConfigurationError(
            "psycopg is required for Python worker access to Supabase tables. Install the ingestion package dependencies."
        ) from exc

    # Bound the TCP connect so a firewalled/unreachable DB fails fast instead of blocking a
    # synchronous request (e.g. the pre-receipt endpoint, which falls back to bundled data)
    # for the OS default of minutes. Overridable via BELLWETHER_DB_CONNECT_TIMEOUT.
    connect_timeout = int(os.getenv("BELLWETHER_DB_CONNECT_TIMEOUT", "10"))
    try:
        return psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=connect_timeout)
    except psycopg.Error as exc:
        message = str(exc)
        if "failed to resolve host" in message:
            raise DatabaseConfigurationError(
                "SUPABASE_DATABASE_URL host could not be resolved. Use the Supabase pooler connection string from Project Settings -> Database -> Connection string."
            ) from exc
        raise DatabaseConfigurationError(
            f"Could not connect to Supabase tables with SUPABASE_DATABASE_URL: {message}"
        ) from exc


@contextmanager
def supabase_connection(settings: ServiceSettings) -> Iterator[Any]:
    connection = open_supabase_connection(settings)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
