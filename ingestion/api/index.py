"""Vercel-compatible ASGI entrypoint.

Vercel can load this module while the implementation remains in the
installable `traceready_ingestion` package.
"""

from traceready_ingestion.api.main import app

__all__ = ["app"]
